"""级联任务分发器 - 父节点分配公众号任务给子节点

功能：
1. 根据 MessageTask 的 cron 策略定时下发任务
2. 将任务持久化到数据库，支持任务互斥
3. 子节点认领任务后其他节点不能再获取
4. 子节点上行文章数据到网关
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from core.db import DB
from core.models.cascade_node import CascadeNode
from core.models.cascade_task_allocation import CascadeTaskAllocation
from core.models.message_task import MessageTask
from core.models.feed import Feed
from core.cascade import CascadeManager, cascade_manager
from core.print import print_info, print_success, print_error, print_warning
from sqlalchemy import and_, or_


class NodeStatus:
    """节点状态"""
    def __init__(self, node: CascadeNode):
        self.node_id = node.id
        self.node_name = node.name
        self.api_url = node.api_url
        self.status = node.status  # 0=离线, 1=在线
        self.last_heartbeat = node.last_heartbeat_at
        self.is_active = node.is_active
        
        # 节点负载状态
        self.current_tasks = 0
        self.max_capacity = 10  # 默认最大并发任务数
        self.feed_quota = {}  # 公众号配额 {mp_id: count}
        
        # 从sync_config读取配置
        if node.sync_config:
            try:
                config = json.loads(node.sync_config)
                self.max_capacity = config.get("max_capacity", 10)
                self.feed_quota = config.get("feed_quota", {})
            except:
                pass

    @property
    def is_online(self) -> bool:
        """节点是否在线"""
        if not self.is_active:
            return False
        if self.status != 1:
            return False
        # 检查心跳是否超时（超过3分钟）
        if self.last_heartbeat:
            heartbeat_age = (datetime.utcnow() - self.last_heartbeat).total_seconds()
            if heartbeat_age > 180:
                return False
        return True

    @property
    def available_capacity(self) -> int:
        """可用容量"""
        return max(0, self.max_capacity - self.current_tasks)

    @property
    def is_available(self) -> bool:
        """是否可用"""
        return self.is_online and self.available_capacity > 0


class CascadeTaskDispatcher:
    """级联任务分发器 - 父节点使用"""
    
    def __init__(self):
        self.manager = cascade_manager
        self.node_statuses: Dict[str, NodeStatus] = {}  # node_id -> NodeStatus

    def refresh_node_statuses(self) -> int:
        """刷新所有子节点状态，并统计当前任务数"""
        session = DB.get_session()
        try:
            child_nodes = session.query(CascadeNode).filter(
                CascadeNode.node_type == 1,
                CascadeNode.is_active == True
            ).all()
            
            online_count = 0
            for node in child_nodes:
                self.node_statuses[node.id] = NodeStatus(node)
                
                # 统计该节点正在执行的任务数
                executing_count = session.query(CascadeTaskAllocation).filter(
                    CascadeTaskAllocation.node_id == node.id,
                    CascadeTaskAllocation.status.in_(['pending', 'claimed', 'executing'])
                ).count()
                self.node_statuses[node.id].current_tasks = executing_count
                
                if self.node_statuses[node.id].is_online:
                    online_count += 1
            
            print_success(f"刷新节点状态完成: 共{len(child_nodes)}个节点, {online_count}个在线")
            return online_count
        except Exception as e:
            print_error(f"刷新节点状态失败: {str(e)}")
            return 0

    def notify_children_new_task(self, allocation_id: str, feed_count: int):
        """
        通知在线子节点有新任务可认领
        
        参数:
            allocation_id: 任务分配ID
            feed_count: 公众号数量
        """
        import httpx
        
        session = DB.get_session()
        try:
            # 获取在线子节点
            online_nodes = session.query(CascadeNode).filter(
                CascadeNode.node_type == 1,
                CascadeNode.status == 1,  # 在线
                CascadeNode.is_active == True
            ).all()
            
            if not online_nodes:
                print_info("没有在线子节点，跳过通知")
                return
            
            print_info(f"通知 {len(online_nodes)} 个在线子节点有新任务")
            
            for node in online_nodes:
                if not node.callback_url:
                    continue
                
                try:
                    # 异步发送通知（不阻塞）
                    asyncio.create_task(self._send_notification(
                        node.callback_url,
                        node.api_key,
                        node.api_secret_hash,
                        {
                            "type": "new_task",
                            "allocation_id": allocation_id,
                            "feed_count": feed_count,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    ))
                except Exception as e:
                    print_warning(f"通知节点 {node.name} 失败: {str(e)}")
                    
        except Exception as e:
            print_error(f"通知子节点失败: {str(e)}")

    async def _send_notification(
        self,
        callback_url: str,
        api_key: str,
        api_secret_hash: str,
        data: dict
    ):
        """发送通知到子节点"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    callback_url,
                    json=data,
                    headers={
                        "Authorization": f"AK-SK {api_key}:{api_secret_hash}",
                        "Content-Type": "application/json"
                    }
                )
                if response.status_code == 200:
                    print_info(f"通知成功: {callback_url}")
                else:
                    print_warning(f"通知失败: {callback_url} - {response.status_code}")
        except Exception as e:
            print_warning(f"通知请求失败: {callback_url} - {str(e)}")

    def select_node_for_feed(self, mp_id: str) -> Optional[str]:
        """
        为指定公众号选择合适的节点
        
        策略:
        1. 检查节点配额配置
        2. 选择可用容量最大的在线节点
        3. 负载均衡：避免单个节点过载
        """
        available_nodes = [
            (node_id, status)
            for node_id, status in self.node_statuses.items()
            if status.is_available
        ]
        
        if not available_nodes:
            return None
        
        # 检查是否有配额配置
        for node_id, status in available_nodes:
            quota = status.feed_quota.get(mp_id, 0)
            if quota > 0:
                # 有配额的节点优先
                return node_id
        
        # 无配额配置，选择负载最轻的节点
        available_nodes.sort(key=lambda x: x[1].current_tasks)
        return available_nodes[0][0]

    def allocate_feeds_to_node(
        self,
        task: MessageTask,
        feeds: List[Feed],
        node_id: str,
        schedule_run_id: str
    ) -> Optional[CascadeTaskAllocation]:
        """
        将公众号分配给指定节点并持久化到数据库
        
        参数:
            task: 任务对象
            feeds: 公众号列表
            node_id: 目标节点ID
            schedule_run_id: 调度批次ID
        
        返回:
            任务分配记录
        """
        session = DB.get_session()
        try:
            if node_id not in self.node_statuses:
                print_error(f"节点不存在: {node_id}")
                return None
            
            node_status = self.node_statuses[node_id]
            if not node_status.is_available:
                print_warning(f"节点不可用: {node_status.node_name}")
                return None
            
            # 检查容量
            required_capacity = len(feeds)
            if required_capacity > node_status.available_capacity:
                print_warning(f"节点 {node_status.node_name} 容量不足: 需要{required_capacity}, 可用{node_status.available_capacity}")
                return None
            
            # 创建分配记录并持久化
            allocation_id = str(uuid.uuid4())
            allocation = CascadeTaskAllocation(
                id=allocation_id,
                task_id=task.id,
                task_name=task.name,
                cron_exp=task.cron_exp,
                node_id=node_id,
                feed_ids=json.dumps([feed.id for feed in feeds]),
                status='pending',
                schedule_run_id=schedule_run_id,
                dispatched_at=datetime.utcnow()
            )
            
            session.add(allocation)
            session.commit()
            
            # 更新内存中的节点任务计数
            node_status.current_tasks += required_capacity
            
            print_success(f"分配任务: {len(feeds)}个公众号 -> {node_status.node_name} (allocation_id: {allocation_id})")
            return allocation
            
        except Exception as e:
            session.rollback()
            print_error(f"分配任务失败: {str(e)}")
            return None

    def create_pending_allocation(
        self,
        task: MessageTask,
        feeds: List[Feed],
        schedule_run_id: str
    ) -> Optional[CascadeTaskAllocation]:
        """
        创建待认领的任务分配记录（不指定节点）
        
        子节点会主动来认领任务
        
        参数:
            task: 任务对象
            feeds: 公众号列表
            schedule_run_id: 调度批次ID
        
        返回:
            任务分配记录
        """
        session = DB.get_session()
        try:
            allocation_id = str(uuid.uuid4())
            allocation = CascadeTaskAllocation(
                id=allocation_id,
                task_id=task.id,
                task_name=task.name,
                cron_exp=task.cron_exp,
                node_id=None,  # 待认领，不指定节点
                feed_ids=json.dumps([feed.id for feed in feeds]),
                status='pending',
                schedule_run_id=schedule_run_id,
                dispatched_at=datetime.utcnow()
            )
            
            session.add(allocation)
            session.commit()
            
            print_success(f"创建待认领任务: {len(feeds)}个公众号 (allocation_id: {allocation_id})")
            return allocation
            
        except Exception as e:
            session.rollback()
            print_error(f"创建待认领任务失败: {str(e)}")
            return None

    def dispatch_task_to_children(
        self,
        task: MessageTask,
        schedule_run_id: str,
        feeds_per_allocation: int = 1
    ) -> bool:
        """
        创建待认领的任务分配记录

        新模式：网关只创建任务记录，不主动分配给节点
        子节点通过 claim_task_for_node 主动认领任务

        每个分配的任务中公众号ID不重复，支持多个子节点并行认领不同公众号

        参数:
            task: 消息任务对象
            schedule_run_id: 调度批次ID
            feeds_per_allocation: 每个任务分配包含的公众号数量，默认1个

        返回:
            是否成功创建任务记录
        """
        print_info(f"开始创建任务记录: {task.name}")

        # 获取任务关联的公众号
        session = DB.get_session()
        try:
            mps_list = json.loads(task.mps_id) if task.mps_id else []
            feed_ids = [mp["id"] for mp in mps_list]

            feeds = session.query(Feed).filter(Feed.id.in_(feed_ids)).all()

            if not feeds:
                print_warning(f"任务 {task.name} 没有关联公众号")
                return False

            print_info(f"任务 {task.name} 包含 {len(feeds)} 个公众号")

            # 将公众号分散到多个任务分配中，确保每个分配的公众号ID不重复
            allocations = []
            total_feeds = len(feeds)
            created_count = 0

            for i in range(0, total_feeds, feeds_per_allocation):
                batch_feeds = feeds[i:i + feeds_per_allocation]

                # 创建待认领的任务分配记录，每个分配包含不重复的公众号
                allocation = self.create_pending_allocation(task, batch_feeds, schedule_run_id)

                if allocation:
                    allocations.append(allocation)
                    created_count += len(batch_feeds)
                    print_info(f"创建任务分配 [{i//feeds_per_allocation + 1}]: {len(batch_feeds)} 个公众号")

            if allocations:
                print_success(f"任务记录创建完成: {created_count} 个公众号分散到 {len(allocations)} 个任务分配等待子节点认领")
                # 通知在线子节点有新任务（通知第一个分配，子节点会继续认领其他分配）
                self.notify_children_new_task(allocations[0].id, total_feeds)
                return True
            else:
                print_warning(f"任务 {task.name} 记录创建失败")
                return False

        except Exception as e:
            print_error(f"创建任务记录失败: {str(e)}")
            return False

    def create_task_package(self, task: MessageTask, feeds: List[Feed], allocation_id: str) -> dict:
        """
        创建任务包（发送给子节点）
        
        参数:
            task: 任务对象
            feeds: 公众号列表
            allocation_id: 分配记录ID
        
        返回:
            任务包字典
        """
        return {
            "allocation_id": allocation_id,
            "task_id": task.id,
            "task_name": task.name,
            "message_type": task.message_type,
            "message_template": task.message_template,
            "web_hook_url": task.web_hook_url,
            "cron_exp": task.cron_exp,
            "headers": task.headers,
            "cookies": task.cookies,
            "feeds": [
                {
                    "id": feed.id,
                    "faker_id": feed.faker_id,
                    "mp_name": feed.mp_name,
                    "mp_cover": feed.mp_cover,
                    "mp_intro": feed.mp_intro,
                    "status": feed.status
                }
                for feed in feeds
            ],
            "dispatched_at": datetime.utcnow().isoformat()
        }

    def claim_task_for_node(self, node_id: str) -> Optional[dict]:
        """
        子节点认领任务（原子操作，实现任务互斥）
        
        新模式：查找 node_id 为空的待认领任务，然后更新为该节点
        
        参数:
            node_id: 子节点ID
        
        返回:
            任务包字典，无任务则返回None
        """
        session = DB.get_session()
        try:
            # 查找待认领的任务（node_id 为空）
            allocation = session.query(CascadeTaskAllocation).filter(
                CascadeTaskAllocation.node_id == None,  # 待认领
                CascadeTaskAllocation.status == 'pending'
            ).order_by(CascadeTaskAllocation.dispatched_at.asc()).first()
            
            if not allocation:
                return None
            
            # 原子更新：设置节点ID和状态
            allocation.node_id = node_id
            allocation.status = 'claimed'
            allocation.claimed_at = datetime.utcnow()
            session.commit()
            
            # 获取任务详情
            task = session.query(MessageTask).filter(
                MessageTask.id == allocation.task_id
            ).first()
            
            if not task:
                print_error(f"任务不存在: {allocation.task_id}")
                allocation.status = 'failed'
                allocation.error_message = "任务不存在"
                session.commit()
                return None
            
            # 获取公众号列表
            feed_ids = json.loads(allocation.feed_ids) if allocation.feed_ids else []
            feeds = session.query(Feed).filter(Feed.id.in_(feed_ids)).all()
            
            # 创建任务包
            task_package = self.create_task_package(task, feeds, allocation.id)
            
            print_info(f"节点 {node_id} 认领任务: {task.name}")
            return task_package
            
        except Exception as e:
            session.rollback()
            print_error(f"认领任务失败: {str(e)}")
            return None

    def update_allocation_status(
        self,
        allocation_id: str,
        status: str,
        result_summary: dict = None,
        error_message: str = None,
        article_count: int = 0,
        new_article_count: int = 0
    ) -> bool:
        """
        更新任务分配状态
        
        参数:
            allocation_id: 分配记录ID
            status: 新状态 (executing, completed, failed)
            result_summary: 结果摘要
            error_message: 错误信息
            article_count: 抓取文章数
            new_article_count: 新文章数
        
        返回:
            是否更新成功
        """
        session = DB.get_session()
        try:
            allocation = session.query(CascadeTaskAllocation).filter(
                CascadeTaskAllocation.id == allocation_id
            ).first()
            
            if not allocation:
                print_error(f"分配记录不存在: {allocation_id}")
                return False
            
            allocation.status = status
            allocation.updated_at = datetime.utcnow()
            
            if status == 'executing':
                allocation.started_at = datetime.utcnow()
            elif status in ['completed', 'failed']:
                allocation.completed_at = datetime.utcnow()
            
            if result_summary:
                allocation.result_summary = json.dumps(result_summary)
            if error_message:
                allocation.error_message = error_message
            
            allocation.article_count = article_count
            allocation.new_article_count = new_article_count
            
            session.commit()
            
            print_info(f"更新任务分配状态: {allocation_id} -> {status}")
            return True
            
        except Exception as e:
            session.rollback()
            print_error(f"更新任务分配状态失败: {str(e)}")
            return False

    def get_pending_allocations(self, node_id: str = None, limit: int = 10) -> List[CascadeTaskAllocation]:
        """
        获取待处理任务分配
        
        参数:
            node_id: 节点ID，不指定则返回所有
            limit: 返回数量限制
        
        返回:
            任务分配列表
        """
        session = DB.get_session()
        try:
            query = session.query(CascadeTaskAllocation).filter(
                CascadeTaskAllocation.status == 'pending'
            )
            
            if node_id:
                query = query.filter(CascadeTaskAllocation.node_id == node_id)
            
            return query.order_by(CascadeTaskAllocation.dispatched_at.asc()).limit(limit).all()
            
        except Exception as e:
            print_error(f"获取待处理任务失败: {str(e)}")
            return []

    def cleanup_timeout_allocations(self, timeout_minutes: int = 30) -> int:
        """
        清理超时的任务分配
        
        参数:
            timeout_minutes: 超时时间（分钟）
        
        返回:
            清理的记录数
        """
        session = DB.get_session()
        try:
            timeout_threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)
            
            # 更新超时的待认领任务
            result = session.query(CascadeTaskAllocation).filter(
                CascadeTaskAllocation.status.in_(['pending', 'claimed', 'executing']),
                CascadeTaskAllocation.dispatched_at < timeout_threshold
            ).update(
                {
                    CascadeTaskAllocation.status: 'timeout',
                    CascadeTaskAllocation.error_message: f'任务超时（>{timeout_minutes}分钟）',
                    CascadeTaskAllocation.completed_at: datetime.utcnow()
                },
                synchronize_session=False
            )
            
            session.commit()
            
            if result > 0:
                print_warning(f"清理了 {result} 个超时任务分配")
            
            return result
            
        except Exception as e:
            session.rollback()
            print_error(f"清理超时任务失败: {str(e)}")
            return 0

    async def dispatch_to_child_node(
        self,
        node_id: str,
        task_package: dict
    ) -> bool:
        """
        将任务包推送到子节点（可选：主动推送模式）
        
        目前采用子节点拉取模式，此方法保留用于将来扩展
        
        参数:
            node_id: 子节点ID
            task_package: 任务包
        
        返回:
            是否成功
        """
        # 当前使用子节点主动拉取模式
        # 此方法保留用于将来实现主动推送
        print_info(f"任务已分配给节点 {node_id}，等待节点拉取")
        return True

    async def execute_dispatch(self, task_id: str = None):
        """
        执行任务分发（立即触发，用于手动分发）

        参数:
            task_id: 任务ID，None则分发所有启用任务
        """
        session = DB.get_session()
        try:
            # 生成调度批次ID
            schedule_run_id = str(uuid.uuid4())

            # 获取任务 (status=1 表示启用状态)
            query = session.query(MessageTask).filter(MessageTask.status == 1)
            if task_id:
                query = query.filter(MessageTask.id == task_id)

            tasks = query.all()

            print_info(f"开始分发 {len(tasks)} 个任务 (批次: {schedule_run_id})")

            for task in tasks:
                # 分发任务
                allocations = self.dispatch_task_to_children(task, schedule_run_id)

            # 清理超时任务
            self.cleanup_timeout_allocations()

            print_success("所有任务分发完成")

        except Exception as e:
            print_error(f"执行分发失败: {str(e)}")


# 全局分发器实例
cascade_task_dispatcher = CascadeTaskDispatcher()


# ========== 网关定时调度服务 ==========
"""启动定时调度服务"""
from core.task import TaskScheduler
cascade_task_scheduler=TaskScheduler()
class CascadeScheduleService:
    """
    网关定时调度服务
    
    根据 MessageTask 的 cron 表达式定时下发任务
    """
    
    def __init__(self):
        self.running = False
        self.scheduler = None
    
    def start(self):
        if cascade_task_scheduler is None:
            print_error("TaskScheduler 未初始化，无法启动定时调度服务")
            return
        self.scheduler = cascade_task_scheduler
        self.running = True
        
        # 加载所有启用的消息任务
        self._load_scheduled_tasks()
        
        print_success("级联定时调度服务已启动")
    def _load_scheduled_tasks(self):
        """加载定时任务"""
        if self.scheduler is None:
            print_error("调度器未初始化，无法加载定时任务")
            return
            
        session = DB.get_session()
        try:
            tasks = session.query(MessageTask).filter(
                MessageTask.status == 1  # 启用状态
            ).all()
            def dispatch_task(task_id):
                    self._dispatch_scheduled_task(task_id)
            for task in tasks:
                if not task.cron_exp:
                    continue
                
                # 添加定时任务
                self.scheduler.add_cron_job(
                    dispatch_task,
                    cron_expr=task.cron_exp,
                    job_id=f"cascade_{task.id}",
                    args=(task.id,),  # 单元素元组必须有逗号
                    tag="级联任务分发"
                )
                print_info(f"已添加级联定时任务: {task.name} ({task.cron_exp})")
            
            # 启动调度器（只需调用一次）
            self.scheduler.start()
            
        except Exception as e:
            print_error(f"加载定时任务失败: {str(e)}")
    
    def _dispatch_scheduled_task(self, task_id: str):
        """执行定时任务分发"""
        session = DB.get_session()
        try:
            task = session.query(MessageTask).filter(
                MessageTask.id == task_id
            ).first()
            
            # status=1 表示启用，非启用状态则跳过
            if not task or task.status != 1:
                return
            
            print_info(f"触发级联定时任务: {task.name}")
            
            # 生成调度批次ID
            schedule_run_id = f"cron_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{task_id}"
            
            # 分发任务
            cascade_task_dispatcher.dispatch_task_to_children(task, schedule_run_id)
            
            # 清理超时任务
            cascade_task_dispatcher.cleanup_timeout_allocations()
            
        except Exception as e:
            print_error(f"执行定时任务分发失败: {str(e)}")
    
    def stop(self):
        """停止调度服务"""
        self.running = False
        if self.scheduler:
            self.scheduler.clear_all_jobs()
        print_info("级联定时调度服务已停止")
    
    def reload(self):
        """重载调度任务"""
        if self.scheduler:
            self.scheduler.clear_all_jobs()
        self._load_scheduled_tasks()
        print_success("级联定时调度任务已重载")


# 全局调度服务实例
cascade_schedule_service = CascadeScheduleService()


# ========== 子节点任务执行 ==========

async def fetch_task_from_parent() -> Optional[dict]:
    """
    子节点从父节点获取分配的任务（带互斥锁）
    
    返回:
        任务包字典，无任务则返回None
    """
    from jobs.cascade_sync import cascade_sync_service
    
    # 如果客户端未初始化，尝试初始化
    if not cascade_sync_service.client:
        print_info("级联客户端未初始化，正在初始化...")
        cascade_sync_service.initialize()
        
        if not cascade_sync_service.client:
            print_warning("级联客户端初始化失败，请检查配置")
            return None
    
    try:
        # 调用父节点的认领任务接口（原子操作）
        task_package = await cascade_sync_service.client.claim_task()
        
        if task_package:
            print_info(f"从父节点获取到任务: {task_package.get('task_name')}")
        
        return task_package
        
    except Exception as e:
        print_error(f"从父节点获取任务失败: {str(e)}")
        return None


async def execute_parent_task(task_package: dict):
    """
    子节点执行父节点分配的任务
    
    参数:
        task_package: 任务包
    """
    from jobs.mps import do_job
    import core.db as db
    
    allocation_id = task_package.get('allocation_id')
    task_name = task_package.get('task_name')
    
    print_info(f"开始执行父节点任务: {task_name}")
    
    try:
        # 通知父节点任务开始执行
        await update_task_status_to_parent(allocation_id, 'executing')
        
        # 创建任务对象
        session = DB.get_session()
        feeds_list = []
        for feed_data in task_package.get("feeds", []):
            feed = session.query(Feed).filter(Feed.id == feed_data["id"]).first()
            if not feed:
                # 创建本地Feed记录
                feed = Feed(
                    id=feed_data["id"],
                    faker_id=feed_data.get("faker_id"),
                    mp_name=feed_data["mp_name"],
                    mp_cover=feed_data["mp_cover"],
                    mp_intro=feed_data["mp_intro"],
                    status=feed_data["status"],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(feed)
            feeds_list.append(feed)
        
        session.commit()
        
        # 创建MessageTask对象
        task = MessageTask(
            id=task_package["task_id"],
            name=task_package["task_name"],
            message_type=task_package["message_type"],
            message_template=task_package["message_template"],
            web_hook_url=task_package["web_hook_url"],
            cron_exp=task_package.get("cron_exp", ""),
            headers=task_package.get("headers", ""),
            cookies=task_package.get("cookies", ""),
            status=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # 为每个公众号执行任务并收集文章数据
        all_articles = []
        results = []
        
        for feed in feeds_list:
            try:
                print_info(f"处理公众号: {feed.mp_name}")
                
                # 执行抓取
                from core.wx import WxGather
                from jobs.article import UpdateArticle
                
                wx = WxGather().Model()
                try:
                    wx.get_Articles(
                        feed.faker_id,
                        CallBack=UpdateArticle,
                        Mps_id=feed.id,
                        Mps_title=feed.mp_name,
                        MaxPage=1
                    )
                except Exception as e:
                    print_error(f"抓取失败 {feed.mp_name}: {str(e)}")
                
                articles = wx.articles if hasattr(wx, 'articles') else []
                count = len(articles)
                
                all_articles.extend(articles)
                
                results.append({
                    "mp_id": feed.id,
                    "mp_name": feed.mp_name,
                    "status": "success",
                    "article_count": count
                })
                
            except Exception as e:
                print_error(f"处理公众号失败 {feed.mp_name}: {str(e)}")
                results.append({
                    "mp_id": feed.id,
                    "mp_name": feed.mp_name,
                    "status": "failed",
                    "error": str(e)
                })
        
        # 上行文章数据到父节点
        if all_articles:
            await upload_articles_to_parent(allocation_id, all_articles)
        
        # 上报执行结果到父节点
        await report_task_completion_to_parent(
            allocation_id=allocation_id,
            task_id=task_package["task_id"],
            results=results,
            article_count=len(all_articles)
        )
        
        print_success(f"任务执行完成: {task_name}")
        
    except Exception as e:
        print_error(f"执行父节点任务失败: {str(e)}")
        # 上报失败状态
        await update_task_status_to_parent(
            allocation_id,
            'failed',
            error_message=str(e)
        )


async def update_task_status_to_parent(
    allocation_id: str,
    status: str,
    error_message: str = None
):
    """更新任务状态到父节点"""
    from jobs.cascade_sync import cascade_sync_service
    
    if not cascade_sync_service.client:
        return
    
    try:
        await cascade_sync_service.client.update_task_status(
            allocation_id=allocation_id,
            status=status,
            error_message=error_message
        )
    except Exception as e:
        print_error(f"更新任务状态失败: {str(e)}")


async def upload_articles_to_parent(allocation_id: str, articles: List[dict]):
    """
    上行文章数据到网关
    
    参数:
        allocation_id: 任务分配ID
        articles: 文章列表
    """
    from jobs.cascade_sync import cascade_sync_service
    
    if not cascade_sync_service.client or not articles:
        return
    
    try:
        print_info(f"上行 {len(articles)} 篇文章到父节点...")
        
        await cascade_sync_service.client.upload_articles(
            allocation_id=allocation_id,
            articles=articles
        )
        
        print_success(f"文章数据上行成功: {len(articles)} 篇")
        
    except Exception as e:
        print_error(f"上行文章数据失败: {str(e)}")


async def report_task_completion_to_parent(
    allocation_id: str,
    task_id: str,
    results: List[dict],
    article_count: int
):
    """上报任务完成结果到父节点"""
    from jobs.cascade_sync import cascade_sync_service
    
    if not cascade_sync_service.client:
        return
    
    try:
        await cascade_sync_service.client.report_task_completion(
            allocation_id=allocation_id,
            task_id=task_id,
            results=results,
            article_count=article_count
        )
        print_success(f"任务结果上报成功")
    except Exception as e:
        print_error(f"上报任务结果失败: {str(e)}")


async def start_child_task_worker(poll_interval: int = 30):
    """
    子节点任务拉取器 - 定期从父节点拉取任务
    
    参数:
        poll_interval: 轮询间隔（秒）
    """
    print_info("启动子节点任务拉取器")
    
    # 初始化级联同步服务
    from jobs.cascade_sync import cascade_sync_service
    if not cascade_sync_service.client:
        print_info("初始化级联同步服务...")
        cascade_sync_service.initialize()
        
        if not cascade_sync_service.client:
            print_error("级联同步服务初始化失败，请检查配置")
            print_error("请确保 config.yaml 中配置了 cascade 参数")
            return
    
    print_success("子节点任务拉取器启动成功")
    
    while True:
        try:
            # 获取任务（带互斥锁）
            task_package = await fetch_task_from_parent()
            
            if task_package:
                # 执行任务
                await execute_parent_task(task_package)
            else:
                print_info("暂无任务，等待下次轮询...")
            
        except Exception as e:
            print_error(f"任务拉取器错误: {str(e)}")
        
        # 等待下次轮询
        await asyncio.sleep(poll_interval)


if __name__ == "__main__":
    import sys
    
    # 测试分发器
    if len(sys.argv) > 1 and sys.argv[1] == "parent":
        # 父节点模式
        print_info("启动父节点任务分发器")
        dispatcher = CascadeTaskDispatcher()
        dispatcher.refresh_node_statuses()
        asyncio.run(dispatcher.execute_dispatch())
    
    elif len(sys.argv) > 1 and sys.argv[1] == "child":
        # 子节点模式
        print_info("启动子节点任务拉取器")
        asyncio.run(start_child_task_worker())
    
    elif len(sys.argv) > 1 and sys.argv[1] == "schedule":
        # 定时调度模式
        print_info("启动网关定时调度服务")
        service = CascadeScheduleService()
        service.start()
        
        try:
            # 保持运行
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            service.stop()
    
    else:
        print("用法:")
        print("  python jobs/cascade_task_dispatcher.py parent   # 父节点手动分发任务")
        print("  python jobs/cascade_task_dispatcher.py child    # 子节点拉取任务")
        print("  python jobs/cascade_task_dispatcher.py schedule # 网关定时调度服务")
