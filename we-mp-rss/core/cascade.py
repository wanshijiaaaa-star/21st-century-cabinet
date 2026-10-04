"""级联系统核心模块 - 支持父子节点架构和同步机制"""

import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from fastapi import HTTPException
import httpx
from core.models.cascade_node import CascadeNode, CascadeSyncLog
from core.models.feed import Feed
from core.models.message_task import MessageTask
import core.db as db
from core.print import print_info, print_success, print_error, print_warning


class CascadeManager:
    """级联系统管理器"""
    
    def __init__(self):
        self.db_session = None
    
    def get_session(self):
        """获取数据库会话"""
        if not self.db_session or not self.db_session.is_active:
            self.db_session = db.DB.get_session()
        return self.db_session
    
    def create_node(
        self,
        node_type: int,
        name: str,
        description: str = "",
        api_url: Optional[str] = None,
        parent_id: Optional[str] = None
    ) -> CascadeNode:
        """
        创建级联节点
        
        参数:
            node_type: 节点类型 (0=父节点, 1=子节点)
            name: 节点名称
            description: 节点描述
            api_url: API地址 (子节点配置父节点地址)
            parent_id: 父节点ID (仅子节点使用)
        
        返回: 创建的节点对象
        """
        session = self.get_session()
        try:
            import uuid
            node_id = str(uuid.uuid4())
            
            node = CascadeNode(
                id=node_id,
                node_type=node_type,
                name=name,
                description=description,
                api_url=api_url,
                parent_id=parent_id,
                status=0,  # 初始为离线
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            session.add(node)
            session.commit()
            session.refresh(node)
            
            print_success(f"创建节点成功: {name} ({node_id})")
            return node
            
        except Exception as e:
            session.rollback()
            print_error(f"创建节点失败: {str(e)}")
            raise
    
    def generate_node_credentials(self, node_id: str) -> Dict[str, str]:
        """
        为子节点生成连接父节点的凭证 (AK/SK)
        
        参数:
            node_id: 节点ID
        
        返回: 包含 AK/SK 的字典
        """
        session = self.get_session()
        try:
            node = session.query(CascadeNode).filter(
                CascadeNode.id == node_id
            ).first()
            
            if not node:
                raise HTTPException(status_code=404, detail="节点不存在")
            
            if node.node_type != 1:
                raise HTTPException(status_code=400, detail="只有子节点需要凭证")
            
            # 生成AK/SK
            api_key = "CN" + secrets.token_urlsafe(32)[:32]  # CN = Cascade Node
            secret_key = "CS" + secrets.token_urlsafe(32)[:32]  # CS = Cascade Secret
            secret_hash = hashlib.sha256(secret_key.encode()).hexdigest()
            
            # 保存到节点
            node.api_key = api_key
            node.api_secret_hash = secret_hash
            node.updated_at = datetime.utcnow()
            session.commit()
            
            print_success(f"为节点 {node.name} 生成凭证")
            
            return {
                "node_id": node_id,
                "api_key": api_key,
                "api_secret": secret_key  # 只在生成时返回一次
            }
            
        except HTTPException:
            raise
        except Exception as e:
            session.rollback()
            print_error(f"生成节点凭证失败: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def verify_node_credentials(self, api_key: str, secret_key: str) -> Optional[CascadeNode]:
        """
        验证子节点凭证
        
        参数:
            api_key: API密钥
            secret_key: 密钥
        
        返回: 验证通过的节点对象，否则返回None
        """
        session = self.get_session()
        try:
            secret_hash = hashlib.sha256(secret_key.encode()).hexdigest()
            
            node = session.query(CascadeNode).filter(
                CascadeNode.api_key == api_key,
                CascadeNode.api_secret_hash == secret_hash,
                CascadeNode.is_active == True
            ).first()
            
            if node:
                # 更新心跳时间
                node.last_heartbeat_at = datetime.utcnow()
                session.commit()
                return node
            
            return None
            
        except Exception as e:
            print_error(f"验证节点凭证失败: {str(e)}")
            return None
    
    def get_parent_node(self) -> Optional[CascadeNode]:
        """获取当前节点的父节点配置"""
        session = self.get_session()
        try:
            # 获取配置为子节点且设置了父节点的记录
            node = session.query(CascadeNode).filter(
                CascadeNode.node_type == 1,
                CascadeNode.is_active == True
            ).first()
            
            return node
            
        except Exception as e:
            print_error(f"获取父节点配置失败: {str(e)}")
            return None
    
    def list_children_nodes(self) -> List[CascadeNode]:
        """获取所有子节点列表（父节点调用）"""
        session = self.get_session()
        try:
            nodes = session.query(CascadeNode).filter(
                CascadeNode.node_type == 1,
                CascadeNode.is_active == True
            ).all()
            
            return nodes
            
        except Exception as e:
            print_error(f"获取子节点列表失败: {str(e)}")
            return []
    
    def create_sync_log(
        self,
        node_id: str,
        operation: str,
        direction: str,
        extra_data: dict = None
    ) -> CascadeSyncLog:
        """
        创建同步日志记录

        参数:
            node_id: 节点ID
            operation: 操作类型
            direction: 方向 (pull/push)
            metadata: 元数据
        
        返回: 同步日志对象
        """
        session = self.get_session()
        try:
            import uuid
            log = CascadeSyncLog(
                id=str(uuid.uuid4()),
                node_id=node_id,
                operation=operation,
                direction=direction,
                status=0,  # 进行中
                extra_data=json.dumps(extra_data or {}),
                started_at=datetime.utcnow()
            )
            
            session.add(log)
            session.commit()
            session.refresh(log)
            
            return log
            
        except Exception as e:
            session.rollback()
            print_error(f"创建同步日志失败: {str(e)}")
            return None
    
    def update_sync_log(
        self,
        log_id: str,
        status: int,
        data_count: int = 0,
        error_message: str = None
    ):
        """
        更新同步日志
        
        参数:
            log_id: 日志ID
            status: 状态 (0=进行中, 1=成功, 2=失败)
            data_count: 数据条数
            error_message: 错误信息
        """
        session = self.get_session()
        try:
            log = session.query(CascadeSyncLog).filter(
                CascadeSyncLog.id == log_id
            ).first()
            
            if log:
                log.status = status
                log.data_count = data_count
                log.error_message = error_message
                log.completed_at = datetime.utcnow()
                session.commit()
                
        except Exception as e:
            session.rollback()
            print_error(f"更新同步日志失败: {str(e)}")


class CascadeClient:
    """子节点客户端 - 用于向父节点同步数据"""
    
    def __init__(self, parent_api_url: str, api_key: str, api_secret: str):
        # 清理和验证URL
        self.parent_api_url = self._clean_url(parent_api_url)
        # 清理 AK/SK 中可能存在的引号
        self.api_key = api_key.strip().strip('"\'') if api_key else ""
        self.api_secret = api_secret.strip().strip('"\'') if api_secret else ""
        self.timeout = 30.0
    
    def _clean_url(self, url: str) -> str:
        """清理和验证URL"""
        if not url:
            raise ValueError("父节点URL不能为空")
        
        # 去除首尾空白和引号
        url = url.strip().strip('"\'')
        
        # 检查是否包含协议
        if not url.startswith(('http://', 'https://')):
            # 自动添加http://
            url = 'http://' + url
            print_warning(f"URL缺少协议，已自动添加: {url}")
        
        # 去除末尾的斜杠
        url = url.rstrip('/')
        
        # 验证URL格式
        if not url.startswith(('http://', 'https://')):
            raise ValueError(f"无效的URL格式: {url}")
        
        return url
    
    def _get_headers(self) -> dict:
        """获取请求头"""
        return {
            "Authorization": f"AK-SK {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json"
        }
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict = None,
        params: dict = None
    ) -> dict:
        """发送HTTP请求到父节点"""
        url = f"{self.parent_api_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                if method.upper() == "GET":
                    response = await client.get(
                        url,
                        headers=self._get_headers(),
                        params=params
                    )
                elif method.upper() == "POST":
                    response = await client.post(
                        url,
                        headers=self._get_headers(),
                        json=data
                    )
                elif method.upper() == "PUT":
                    response = await client.put(
                        url,
                        headers=self._get_headers(),
                        json=data
                    )
                else:
                    raise ValueError(f"不支持的HTTP方法: {method}")
                
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                print_error(f"请求父节点失败: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                print_error(f"请求父节点异常: {str(e)}")
                raise
    
    async def pull_feeds(self) -> List[dict]:
        """从父节点拉取公众号数据"""
        print_info("从父节点拉取公众号数据...")
        result = await self._request("GET", "/api/v1/wx/cascade/feeds")
        return result.get("data", [])
    
    async def pull_message_tasks(self) -> List[dict]:
        """从父节点拉取消息任务"""
        print_info("从父节点拉取消息任务...")
        result = await self._request("GET", "/api/v1/wx/cascade/message-tasks")
        return result.get("data", [])
    
    async def report_task_result(
        self,
        task_id: str,
        results: List[dict]
    ) -> dict:
        """
        向父节点上报任务执行结果
        
        参数:
            task_id: 任务ID
            results: 执行结果列表
        
        返回: 父节点响应
        """
        print_info(f"向父节点上报任务结果: {task_id}")
        data = {
            "task_id": task_id,
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
        result = await self._request("POST", "/api/v1/wx/cascade/report-result", data=data)
        return result
    
    async def send_heartbeat(self, callback_url: str = None) -> dict:
        """
        发送心跳到父节点
        
        参数:
            callback_url: 可选，子节点的通知回调地址
        """
        try:
            data = {}
            if callback_url:
                data["callback_url"] = callback_url
            result = await self._request("POST", "/api/v1/wx/cascade/heartbeat", data=data if data else None)
            print_info("心跳发送成功")
            return result
        except Exception as e:
            print_error(f"心跳发送失败: {str(e)}")
            raise
    
    async def get_pending_tasks(self, limit: int = 1) -> dict:
        """
        从父节点获取待处理任务
        
        参数:
            limit: 每次获取的任务数量限制
        
        返回:
            任务包字典，无任务则返回None
        """
        try:
            result = await self._request("GET", "/api/v1/wx/cascade/pending-tasks", params={"limit": limit})
            data = result.get("data")
            # 确保返回有效的任务包（包含task_id）或None
            if data and isinstance(data, dict) and "task_id" in data:
                return data
            return None
        except Exception as e:
            print_error(f"获取待处理任务失败: {str(e)}")
            raise

    async def claim_task(self) -> dict:
        """
        子节点认领任务（原子操作，带互斥锁）
        
        返回:
            任务包字典，无任务则返回None
        """
        try:
            result = await self._request("POST", "/api/v1/wx/cascade/claim-task")
            data = result.get("data")
            if data and isinstance(data, dict) and "allocation_id" in data:
                return data
            return None
        except Exception as e:
            print_error(f"认领任务失败: {str(e)}")
            raise

    async def update_task_status(
        self,
        allocation_id: str,
        status: str,
        error_message: str = None
    ) -> dict:
        """
        更新任务分配状态
        
        参数:
            allocation_id: 分配记录ID
            status: 状态 (executing, completed, failed)
            error_message: 错误信息
        
        返回:
            父节点响应
        """
        data = {
            "allocation_id": allocation_id,
            "status": status,
            "error_message": error_message,
            "timestamp": datetime.utcnow().isoformat()
        }
        result = await self._request("PUT", "/api/v1/wx/cascade/task-status", data=data)
        return result

    async def upload_articles(
        self,
        allocation_id: str,
        articles: List[dict]
    ) -> dict:
        """
        上行文章数据到网关
        
        参数:
            allocation_id: 任务分配ID
            articles: 文章列表
        
        返回:
            父节点响应
        """
        data = {
            "allocation_id": allocation_id,
            "articles": articles,
            "timestamp": datetime.utcnow().isoformat()
        }
        result = await self._request("POST", "/api/v1/wx/cascade/upload-articles", data=data)
        return result

    async def report_task_completion(
        self,
        allocation_id: str,
        task_id: str,
        results: List[dict],
        article_count: int
    ) -> dict:
        """
        上报任务完成结果
        
        参数:
            allocation_id: 分配记录ID
            task_id: 任务ID
            results: 执行结果列表
            article_count: 文章数量
        
        返回:
            父节点响应
        """
        data = {
            "allocation_id": allocation_id,
            "task_id": task_id,
            "results": results,
            "article_count": article_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        result = await self._request("POST", "/api/v1/wx/cascade/report-completion", data=data)
        return result


# 全局级联管理器实例
cascade_manager = CascadeManager()
