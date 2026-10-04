"""级联系统API接口"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Request
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from core.auth import get_current_user_or_ak
from core.db import DB
from core.cascade import cascade_manager, CascadeClient
from core.models.cascade_node import CascadeNode, CascadeSyncLog
from core.models.feed import Feed
from core.models.message_task import MessageTask
from .base import success_response, error_response
from core.print import print_info, print_success, print_error
import json

router = APIRouter(prefix="/cascade", tags=["级联管理"])


# ===== 请求模型 =====

class CreateNodeRequest(BaseModel):
    """创建节点请求"""
    node_type: int  # 0=父节点, 1=子节点
    name: str
    description: Optional[str] = ""
    api_url: Optional[str] = None  # 子节点配置父节点地址时使用


class UpdateNodeRequest(BaseModel):
    """更新节点请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    api_url: Optional[str] = None
    is_active: Optional[bool] = None
    sync_config: Optional[dict] = None


class NodeCredentialRequest(BaseModel):
    """获取节点凭证请求"""
    node_id: str


class TestConnectionRequest(BaseModel):
    """测试连接请求"""
    api_url: str
    api_key: str
    api_secret: str


class SyncDataRequest(BaseModel):
    """同步数据请求"""
    node_id: str
    data_type: str  # feeds, tasks, all


class ReportResultRequest(BaseModel):
    """上报任务结果请求"""
    task_id: str
    results: List[dict]
    timestamp: str


class ClaimTaskRequest(BaseModel):
    """认领任务请求（无需参数，从认证信息获取节点ID）"""
    pass


class UpdateTaskStatusRequest(BaseModel):
    """更新任务状态请求"""
    allocation_id: str
    status: str
    error_message: Optional[str] = None
    timestamp: str


class UploadArticlesRequest(BaseModel):
    """上行文章数据请求"""
    allocation_id: str
    articles: List[dict]
    timestamp: str


class ReportCompletionRequest(BaseModel):
    """上报任务完成请求"""
    allocation_id: str
    task_id: str
    results: List[dict]
    article_count: int
    timestamp: str


# ===== 节点管理接口 =====

@router.post("/nodes", summary="创建级联节点")
async def create_node(
    req: CreateNodeRequest,
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    创建级联节点
    
    - node_type=0: 父节点 (本节点)
    - node_type=1: 子节点 (需要连接到父节点)
    """
    session = DB.get_session()
    try:
        node = cascade_manager.create_node(
            node_type=req.node_type,
            name=req.name,
            description=req.description,
            api_url=req.api_url
        )
        
        return success_response(
            {
                "node_id": node.id,
                "node_type": node.node_type,
                "name": node.name,
                "is_active": node.is_active,
                "created_at": node.created_at.isoformat()
            },
            "节点创建成功"
        )
    except Exception as e:
        return error_response(code=500, message=str(e))


@router.get("/nodes", summary="获取节点列表")
async def list_nodes(
    node_type: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    获取级联节点列表
    
    参数:
        node_type: 可选，按节点类型筛选 (0=父节点, 1=子节点)
    """
    session = DB.get_session()
    try:
        query = session.query(CascadeNode)
        
        if node_type is not None:
            query = query.filter(CascadeNode.node_type == node_type)
        
        nodes = query.all()
        
        # 返回时不暴露api_secret_hash
        node_list = []
        for node in nodes:
            node_data = {
                "id": node.id,
                "node_type": node.node_type,
                "name": node.name,
                "description": node.description,
                "api_url": node.api_url,
                "api_key": node.api_key,
                "parent_id": node.parent_id,
                "status": node.status,
                "is_active": node.is_active,
                "last_sync_at": node.last_sync_at.isoformat() if node.last_sync_at else None,
                "last_heartbeat_at": node.last_heartbeat_at.isoformat() if node.last_heartbeat_at else None,
                "created_at": node.created_at.isoformat(),
                "updated_at": node.updated_at.isoformat()
            }
            
            if node.sync_config:
                try:
                    node_data["sync_config"] = json.loads(node.sync_config)
                except:
                    node_data["sync_config"] = {}
            
            node_list.append(node_data)
        
        return success_response(node_list)
    except Exception as e:
        return error_response(code=500, message=str(e))


@router.get("/nodes/{node_id}", summary="获取节点详情")
async def get_node(
    node_id: str,
    current_user: dict = Depends(get_current_user_or_ak)
):
    session = DB.get_session()
    try:
        node = session.query(CascadeNode).filter(CascadeNode.id == node_id).first()
        
        if not node:
            raise HTTPException(status_code=404, detail="节点不存在")
        
        return success_response(node)
    except HTTPException:
        raise
    except Exception as e:
        return error_response(code=500, message=str(e))


@router.put("/nodes/{node_id}", summary="更新节点")
async def update_node(
    node_id: str,
    req: UpdateNodeRequest,
    current_user: dict = Depends(get_current_user_or_ak)
):
    session = DB.get_session()
    try:
        node = session.query(CascadeNode).filter(CascadeNode.id == node_id).first()
        
        if not node:
            raise HTTPException(status_code=404, detail="节点不存在")
        
        if req.name is not None:
            node.name = req.name
        if req.description is not None:
            node.description = req.description
        if req.api_url is not None:
            node.api_url = req.api_url
        if req.is_active is not None:
            node.is_active = req.is_active
        if req.sync_config is not None:
            node.sync_config = json.dumps(req.sync_config)
        
        node.updated_at = datetime.utcnow()
        session.commit()
        
        return success_response(message="节点更新成功")
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        return error_response(code=500, message=str(e))


@router.delete("/nodes/{node_id}", summary="删除节点")
async def delete_node(
    node_id: str,
    current_user: dict = Depends(get_current_user_or_ak)
):
    session = DB.get_session()
    try:
        node = session.query(CascadeNode).filter(CascadeNode.id == node_id).first()
        
        if not node:
            raise HTTPException(status_code=404, detail="节点不存在")
        
        session.delete(node)
        session.commit()
        
        return success_response(message="节点删除成功")
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        return error_response(code=500, message=str(e))


@router.post("/nodes/{node_id}/credentials", summary="生成节点凭证")
async def generate_node_credentials(
    node_id: str,
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    为子节点生成连接父节点的凭证 (AK/SK)
    仅返回一次，请妥善保存
    """
    try:
        credentials = cascade_manager.generate_node_credentials(node_id)
        return success_response(credentials, "凭证生成成功")
    except HTTPException:
        raise
    except Exception as e:
        return error_response(code=500, message=str(e))


@router.post("/nodes/{node_id}/test-connection", summary="测试节点连接")
async def test_node_connection(
    node_id: str,
    req: TestConnectionRequest = None,
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    测试子节点到父节点的连接
    
    如果提供req参数，使用提供的凭证测试
    否则使用节点配置中的凭证
    """
    session = DB.get_session()
    try:
        node = session.query(CascadeNode).filter(CascadeNode.id == node_id).first()
        
        if not node:
            raise HTTPException(status_code=404, detail="节点不存在")
        
        if req:
            api_url = req.api_url
            api_key = req.api_key
            api_secret = req.api_secret
        else:
            api_url = node.api_url
            api_key = node.api_key
            api_secret = ""  # 无法获取原始secret
        
        # 创建客户端并测试连接
        client = CascadeClient(api_url, api_key, api_secret)
        result = await client.send_heartbeat()
        
        return success_response(
            {"connected": True, "parent_response": result},
            "连接测试成功"
        )
        
    except Exception as e:
        print_error(f"连接测试失败: {str(e)}")
        return success_response(
            {"connected": False, "error": str(e)},
            "连接测试失败"
        )


# ===== 数据同步接口（子节点调用）=====

@router.get("/feeds", summary="获取父节点公众号数据")
async def get_feeds(
    request: Request,
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    子节点从父节点拉取公众号数据
    
    需要级联认证
    """
    session = DB.get_session()
    try:
        feeds = session.query(Feed).all()
        
        feed_list = []
        for feed in feeds:
            feed_list.append({
                "id": feed.id,
                "faker_id": feed.faker_id,
                "mp_name": feed.mp_name,
                "mp_cover": feed.mp_cover,
                "mp_intro": feed.mp_intro,
                "status": feed.status,
                "created_at": feed.created_at.isoformat() if feed.created_at else None,
                "updated_at": feed.updated_at.isoformat() if feed.updated_at else None
            })
        
        return success_response(feed_list)
    except Exception as e:
        return error_response(code=500, message=str(e))


@router.get("/message-tasks", summary="获取父节点消息任务")
async def get_message_tasks(
    request: Request,
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    子节点从父节点拉取消息任务
    
    需要级联认证
    """
    session = DB.get_session()
    try:
        tasks = session.query(MessageTask).filter(
            MessageTask.status == 0  # 只返回启用状态的任务
        ).all()
        
        task_list = []
        for task in tasks:
            task_list.append({
                "id": task.id,
                "name": task.name,
                "message_type": task.message_type,
                "message_template": task.message_template,
                "web_hook_url": task.web_hook_url,
                "mps_id": task.mps_id,
                "cron_exp": task.cron_exp,
                "status": task.status,
                "headers": task.headers,
                "cookies": task.cookies,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None
            })
        
        return success_response(task_list)
    except Exception as e:
        return error_response(code=500, message=str(e))


@router.post("/report-result", summary="上报任务执行结果")
async def report_task_result(
    req: ReportResultRequest,
    request: Request,
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    子节点向父节点上报任务执行结果
    
    需要级联认证
    """
    session = DB.get_session()
    try:
        # TODO: 实现结果上报逻辑
        # 可以将结果存储到单独的结果表或日志表中
        
        print_info(f"收到任务结果上报: task_id={req.task_id}, results数量={len(req.results)}")
        
        # 创建同步日志
        from core.cascade import cascade_manager
        node_id = current_user.get("node_id", "unknown")
        log = cascade_manager.create_sync_log(
            node_id=node_id,
            operation="report_result",
            direction="push",
            extra_data={
                "task_id": req.task_id,
                "result_count": len(req.results)
            }
        )
        
        if log:
            cascade_manager.update_sync_log(log.id, status=1, data_count=len(req.results))
        
        return success_response(message="结果上报成功")
    except Exception as e:
        return error_response(code=500, message=str(e))


@router.post("/heartbeat", summary="心跳接口")
async def heartbeat(
    request: Request,
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    子节点心跳接口
    
    用于保持连接活跃，并可注册回调地址
    """
    try:
        # 获取认证信息中的节点ID
        auth_header = request.headers.get("Authorization", "")
        callback_url = None
        
        # 尝试获取回调地址
        try:
            body = await request.json()
            callback_url = body.get("callback_url") if body else None
        except:
            pass
        
        if auth_header.startswith("AK-SK "):
            credentials = auth_header[6:].strip()
            api_key = credentials.split(':')[0] if ':' in credentials else credentials
            
            # 查找对应节点并更新状态
            session = DB.get_session()
            node = session.query(CascadeNode).filter(
                CascadeNode.api_key == api_key
            ).first()
            
            if node:
                node.status = 1  # 在线
                node.last_heartbeat_at = datetime.utcnow()
                # 更新回调地址
                if callback_url:
                    node.callback_url = callback_url
                session.commit()
        
        return success_response({"status": "alive"})
    except Exception as e:
        return error_response(code=500, message=str(e))


@router.post("/notify", summary="接收父节点通知（子节点使用）")
async def receive_notification(
    request: Request,
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    子节点接收父节点的任务通知
    
    当网关有新任务时，会主动通知子节点来认领
    """
    try:
        body = await request.json()
        notification_type = body.get("type")
        
        print_info(f"收到父节点通知: {notification_type}")
        
        # 检查是否为子节点
        from core.config import cfg
        if cfg.get("cascade.node_type") != "child":
            return error_response(code=400, message="仅子节点可接收通知")
        
        # 处理通知
        from jobs.cascade_sync import cascade_sync_service
        import asyncio
        
        if cascade_sync_service.sync_enabled:
            # 异步处理通知
            asyncio.create_task(cascade_sync_service.handle_task_notification(body))
            return success_response(message="通知已接收")
        else:
            return error_response(code=400, message="同步服务未启用")
            
    except Exception as e:
        print_error(f"处理通知失败: {str(e)}")
        return error_response(code=500, message=str(e))


# ===== 同步日志接口 =====

@router.get("/sync-logs", summary="获取同步日志")
async def list_sync_logs(
    node_id: Optional[str] = Query(None),
    operation: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    获取同步日志
    
    参数:
        node_id: 可选，按节点ID筛选
        operation: 可选，按操作类型筛选
        limit: 每页数量
        offset: 偏移量
    """
    session = DB.get_session()
    try:
        query = session.query(CascadeSyncLog)
        
        if node_id:
            query = query.filter(CascadeSyncLog.node_id == node_id)
        if operation:
            query = query.filter(CascadeSyncLog.operation == operation)
        
        total = query.count()
        logs = query.order_by(CascadeSyncLog.started_at.desc()).limit(limit).offset(offset).all()
        
        log_list = []
        for log in logs:
            log_data = {
                "id": log.id,
                "node_id": log.node_id,
                "operation": log.operation,
                "direction": log.direction,
                "status": log.status,
                "data_count": log.data_count,
                "error_message": log.error_message,
                "extra_data": json.loads(log.extra_data) if log.extra_data else {},
                "started_at": log.started_at.isoformat() if log.started_at else None,
                "completed_at": log.completed_at.isoformat() if log.completed_at else None
            }
            log_list.append(log_data)
        
        return success_response({
            "list": log_list,
            "page": {
                "limit": limit,
                "offset": offset
            },
            "total": total
        })
    except Exception as e:
        return error_response(code=500, message=str(e))


# ===== 任务分发接口（父节点专用） =====

@router.get("/pending-tasks", summary="子节点获取待处理任务（旧接口，建议使用claim-task）")
async def get_pending_tasks(
    request: Request,
    node_id: str = Query(None, description="节点ID"),
    limit: int = Query(1, ge=1, le=10),
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    子节点从父节点获取分配的任务（旧接口）
    
    建议使用 POST /claim-task 接口，支持任务互斥
    """
    from jobs.cascade_task_dispatcher import cascade_task_dispatcher
    
    session = DB.get_session()
    try:
        # 从认证信息中获取节点ID
        if not node_id:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("AK-SK "):
                credentials = auth_header[6:].strip()
                api_key = credentials.split(':')[0] if ':' in credentials else credentials
                
                node = session.query(CascadeNode).filter(
                    CascadeNode.api_key == api_key
                ).first()
                if node:
                    node_id = node.id
        
        if not node_id:
            return error_response(code=400, message="无法确定节点ID")
        
        # 使用新的认领任务方法
        task_package = cascade_task_dispatcher.claim_task_for_node(node_id)
        
        if not task_package:
            return success_response(None, "暂无待处理任务")
        
        return success_response(task_package, "获取任务成功")
        
    except Exception as e:
        print_error(f"获取待处理任务失败: {str(e)}")
        return error_response(code=500, message=str(e))


@router.post("/claim-task", summary="子节点认领任务（原子操作，支持互斥）")
async def claim_task(
    request: Request,
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    子节点认领任务（原子操作，支持任务互斥）
    
    使用数据库事务确保同一时间只有一个节点能获取同一任务。
    子节点收到任务后，其他节点不能再收到该任务。
    
    需要级联认证（AK/SK）
    """
    from jobs.cascade_task_dispatcher import cascade_task_dispatcher
    from core.models.cascade_task_allocation import CascadeTaskAllocation
    
    session = DB.get_session()
    try:
        # 从认证信息中获取节点ID
        node_id = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("AK-SK "):
            credentials = auth_header[6:].strip()
            api_key = credentials.split(':')[0] if ':' in credentials else credentials
            
            node = session.query(CascadeNode).filter(
                CascadeNode.api_key == api_key
            ).first()
            if node:
                node_id = node.id
        
        if not node_id:
            return error_response(code=400, message="无法确定节点ID")
        
        # 使用原子操作认领任务
        task_package = cascade_task_dispatcher.claim_task_for_node(node_id)
        
        if not task_package:
            return success_response(None, "暂无待处理任务")
        
        return success_response(task_package, "认领任务成功")
        
    except Exception as e:
        print_error(f"认领任务失败: {str(e)}")
        return error_response(code=500, message=str(e))


@router.put("/task-status", summary="更新任务分配状态")
async def update_task_status(
    req: UpdateTaskStatusRequest,
    request: Request,
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    子节点更新任务分配状态
    
    参数:
        allocation_id: 分配记录ID
        status: 状态 (executing, completed, failed)
        error_message: 错误信息（可选）
    """
    from jobs.cascade_task_dispatcher import cascade_task_dispatcher
    
    try:
        success = cascade_task_dispatcher.update_allocation_status(
            allocation_id=req.allocation_id,
            status=req.status,
            error_message=req.error_message
        )
        
        if not success:
            return error_response(code=404, message="分配记录不存在")
        
        return success_response(message="状态更新成功")
        
    except Exception as e:
        print_error(f"更新任务状态失败: {str(e)}")
        return error_response(code=500, message=str(e))


@router.post("/upload-articles", summary="子节点上行文章数据到网关")
async def upload_articles(
    req: UploadArticlesRequest,
    request: Request,
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    子节点上行文章数据到网关
    
    子节点执行抓取任务后，将文章数据上传到父节点保存。
    
    参数:
        allocation_id: 任务分配ID
        articles: 文章列表
    """
    from core.models.article import Article
    from core.models.cascade_task_allocation import CascadeTaskAllocation
    
    session = DB.get_session()
    try:
        # 验证分配记录
        allocation = session.query(CascadeTaskAllocation).filter(
            CascadeTaskAllocation.id == req.allocation_id
        ).first()
        
        if not allocation:
            return error_response(code=404, message="分配记录不存在")
        
        # 保存文章到数据库
        new_count = 0
        for article_data in req.articles:
            # 检查文章是否已存在
            existing = session.query(Article).filter(
                Article.id == article_data.get("id")
            ).first()
            
            if not existing:
                # 创建新文章
                article = Article(
                    id=article_data.get("id"),
                    mp_id=article_data.get("mp_id"),
                    title=article_data.get("title"),
                    pic_url=article_data.get("pic_url"),
                    url=article_data.get("url"),
                    description=article_data.get("description"),
                    content=article_data.get("content"),
                    status=article_data.get("status", 1),
                    publish_time=article_data.get("publish_time"),
                    created_at=datetime.utcnow(),
                    updated_at=int(datetime.utcnow().timestamp()),
                    updated_at_millis=int(datetime.utcnow().timestamp() * 1000)
                )
                session.add(article)
                new_count += 1
            else:
                # 更新现有文章
                existing.title = article_data.get("title", existing.title)
                existing.content = article_data.get("content", existing.content)
                existing.updated_at = int(datetime.utcnow().timestamp())
                existing.updated_at_millis = int(datetime.utcnow().timestamp() * 1000)
        
        # 更新分配记录的文章统计
        allocation.article_count = len(req.articles)
        allocation.new_article_count = new_count
        
        session.commit()
        
        print_success(f"接收文章数据: {len(req.articles)}篇, 新增{new_count}篇")
        
        return success_response({
            "received": len(req.articles),
            "new_count": new_count
        }, "文章数据上行成功")
        
    except Exception as e:
        session.rollback()
        print_error(f"上行文章数据失败: {str(e)}")
        return error_response(code=500, message=str(e))


@router.post("/report-completion", summary="子节点上报任务完成")
async def report_completion(
    req: ReportCompletionRequest,
    request: Request,
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    子节点上报任务完成结果
    
    参数:
        allocation_id: 分配记录ID
        task_id: 任务ID
        results: 执行结果列表
        article_count: 文章数量
    """
    from jobs.cascade_task_dispatcher import cascade_task_dispatcher
    
    try:
        # 更新分配记录状态
        success = cascade_task_dispatcher.update_allocation_status(
            allocation_id=req.allocation_id,
            status='completed',
            result_summary={
                "task_id": req.task_id,
                "results": req.results,
                "article_count": req.article_count
            },
            article_count=req.article_count
        )
        
        if not success:
            return error_response(code=404, message="分配记录不存在")
        
        # 创建同步日志
        node_id = current_user.get("node_id", "unknown")
        log = cascade_manager.create_sync_log(
            node_id=node_id,
            operation="task_completion",
            direction="push",
            extra_data={
                "allocation_id": req.allocation_id,
                "task_id": req.task_id,
                "article_count": req.article_count,
                "result_count": len(req.results)
            }
        )
        
        if log:
            cascade_manager.update_sync_log(log.id, status=1, data_count=req.article_count)
        
        return success_response(message="任务完成上报成功")
        
    except Exception as e:
        print_error(f"上报任务完成失败: {str(e)}")
        return error_response(code=500, message=str(e))


@router.post("/dispatch-task", summary="手动触发任务分发")
async def dispatch_tasks(
    task_id: Optional[str] = Query(None, description="任务ID，不指定则分发所有任务"),
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    手动触发任务分发（父节点使用）

    将任务分配给各个在线的子节点
    """
    from jobs.cascade_task_dispatcher import cascade_task_dispatcher
    from core.models.cascade_task_allocation import CascadeTaskAllocation

    try:
        # 刷新节点状态
        online_count = cascade_task_dispatcher.refresh_node_statuses()

        # 检查任务数量 (status=1 表示启用状态)
        session = DB.get_session()
        query = session.query(MessageTask).filter(MessageTask.status == 1)
        if task_id:
            query = query.filter(MessageTask.id == task_id)
        tasks = query.all()
        
        task_info = []
        for task in tasks:
            mps_list = json.loads(task.mps_id) if task.mps_id else []
            task_info.append({
                "id": task.id,
                "name": task.name,
                "mp_count": len(mps_list)
            })
        
        # 执行分发
        await cascade_task_dispatcher.execute_dispatch(task_id)
        
        # 获取分配数量（从数据库）
        allocation_count = session.query(CascadeTaskAllocation).filter(
            CascadeTaskAllocation.status == 'pending'
        ).count()
        
        return success_response({
            "online_nodes": online_count,
            "task_count": len(tasks),
            "tasks": task_info,
            "allocations_created": allocation_count
        }, "任务分发完成")
        
    except Exception as e:
        print_error(f"任务分发失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return error_response(code=500, message=str(e))


@router.get("/allocations", summary="查看任务分配情况")
async def get_allocations(
    task_id: Optional[str] = Query(None),
    node_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    查看任务分配情况（从数据库读取）
    
    参数:
        task_id: 按任务ID筛选
        node_id: 按节点ID筛选
        status: 按状态筛选 (pending, claimed, executing, completed, failed, timeout)
        limit: 每页数量
        offset: 偏移量
    """
    from core.models.cascade_task_allocation import CascadeTaskAllocation
    
    session = DB.get_session()
    try:
        query = session.query(CascadeTaskAllocation)
        
        if task_id:
            query = query.filter(CascadeTaskAllocation.task_id == task_id)
        if node_id:
            query = query.filter(CascadeTaskAllocation.node_id == node_id)
        if status:
            query = query.filter(CascadeTaskAllocation.status == status)
        
        total = query.count()
        allocations = query.order_by(
            CascadeTaskAllocation.dispatched_at.desc()
        ).limit(limit).offset(offset).all()
        
        allocation_list = [alloc.to_dict() for alloc in allocations]
        
        # 添加节点名称
        for alloc_data in allocation_list:
            node = session.query(CascadeNode).filter(
                CascadeNode.id == alloc_data["node_id"]
            ).first()
            if node:
                alloc_data["node_name"] = node.name
        
        return success_response({
            "list": allocation_list,
            "total": total,
            "page": {
                "limit": limit,
                "offset": offset
            }
        })
        
    except Exception as e:
        return error_response(code=500, message=str(e))


@router.post("/start-scheduler", summary="启动网关定时调度服务")
async def start_scheduler(
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    启动网关定时调度服务
    
    根据 MessageTask 的 cron 表达式定时下发任务
    """
    from jobs.cascade_task_dispatcher import cascade_schedule_service
    
    try:
        cascade_schedule_service.start()
        return success_response(message="定时调度服务已启动")
    except Exception as e:
        return error_response(code=500, message=str(e))


@router.post("/stop-scheduler", summary="停止网关定时调度服务")
async def stop_scheduler(
    current_user: dict = Depends(get_current_user_or_ak)
):
    """停止网关定时调度服务"""
    from jobs.cascade_task_dispatcher import cascade_schedule_service
    
    try:
        cascade_schedule_service.stop()
        return success_response(message="定时调度服务已停止")
    except Exception as e:
        return error_response(code=500, message=str(e))


@router.post("/reload-scheduler", summary="重载网关定时调度任务")
async def reload_scheduler(
    current_user: dict = Depends(get_current_user_or_ak)
):
    """重载网关定时调度任务"""
    from jobs.cascade_task_dispatcher import cascade_schedule_service
    
    try:
        cascade_schedule_service.reload()
        return success_response(message="定时调度任务已重载")
    except Exception as e:
        return error_response(code=500, message=str(e))


@router.get("/feed-status", summary="查看各公众号更新状态")
async def get_feed_status(
    feed_id: Optional[str] = Query(None, description="公众号ID，不指定则返回所有"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort_by: Optional[str] = Query(None, description="排序字段: mp_name, article_count, update_status, latest_article_time, updated_at"),
    sort_order: Optional[str] = Query("desc", description="排序方向: asc, desc"),
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    查看各公众号的更新状态
    
    返回每个公众号的：
    - 基本信息
    - 最近抓取时间
    - 文章数量
    - 最后执行的任务状态和执行节点
    """
    from core.models.cascade_task_allocation import CascadeTaskAllocation
    from core.models.article import Article
    from sqlalchemy import func
    
    session = DB.get_session()
    try:
        # 构建查询
        query = session.query(Feed)
        if feed_id:
            query = query.filter(Feed.id == feed_id)
        
        # 先计算总数
        total = query.count()
        
        # 再分页
        feeds = query.limit(limit).offset(offset).all()
        
        feed_status_list = []
        for feed in feeds:
            # 获取文章数量
            article_count = session.query(Article).filter(
                Article.mp_id == feed.id
            ).count()
            
            # 获取最近一篇文章的时间和来源节点
            latest_article = session.query(Article).filter(
                Article.mp_id == feed.id
            ).order_by(Article.created_at.desc()).first()
            
            latest_article_time = latest_article.created_at.isoformat() if latest_article and latest_article.created_at else None
            
            # 获取该公众号相关的最近完成的任务分配（包含节点信息）
            recent_allocation = session.query(CascadeTaskAllocation).filter(
                CascadeTaskAllocation.feed_ids.like(f'%"{feed.id}"%'),
                CascadeTaskAllocation.status.in_(['completed', 'failed'])
            ).order_by(CascadeTaskAllocation.completed_at.desc()).first()
            
            last_task_status = None
            last_task_time = None
            last_task_node_id = None
            last_task_node_name = None
            
            if recent_allocation:
                last_task_status = recent_allocation.status
                last_task_time = recent_allocation.completed_at.isoformat() if recent_allocation.completed_at else None
                last_task_node_id = recent_allocation.node_id
                
                # 获取节点名称
                if recent_allocation.node_id:
                    node = session.query(CascadeNode).filter(
                        CascadeNode.id == recent_allocation.node_id
                    ).first()
                    last_task_node_name = node.name if node else None
            
            # 计算更新状态
            update_status = "unknown"
            if feed.update_time:
                import time
                hours_since_update = (int(time.time()) - feed.update_time) / 3600
                if hours_since_update < 1:
                    update_status = "fresh"  # 1小时内更新
                elif hours_since_update < 24:
                    update_status = "recent"  # 24小时内更新
                elif hours_since_update < 72:
                    update_status = "stale"  # 3天内更新
                else:
                    update_status = "outdated"  # 超过3天
            
            feed_status_list.append({
                "id": feed.id,
                "mp_name": feed.mp_name,
                "mp_cover": feed.mp_cover,
                "status": feed.status,
                "article_count": article_count,
                "latest_article_time": latest_article_time,
                "update_status": update_status,
                "update_time": feed.update_time,
                "sync_time": feed.sync_time,
                "last_task": {
                    "status": last_task_status,
                    "time": last_task_time,
                    "node_id": last_task_node_id,
                    "node_name": last_task_node_name
                } if last_task_status else None,
                "created_at": feed.created_at.isoformat() if feed.created_at else None,
                "updated_at": feed.updated_at.isoformat() if feed.updated_at else None
            })
        
        # 排序逻辑
        if sort_by:
            # 动态排序
            reverse = sort_order == "desc"
            if sort_by == "update_status":
                status_order = {"outdated": 0, "stale": 1, "unknown": 2, "recent": 3, "fresh": 4}
                feed_status_list.sort(key=lambda x: status_order.get(x.get("update_status", "unknown"), 2), reverse=reverse)
            elif sort_by == "latest_article_time":
                feed_status_list.sort(key=lambda x: x.get("latest_article_time") or "", reverse=reverse)
            elif sort_by == "article_count":
                feed_status_list.sort(key=lambda x: x.get("article_count", 0), reverse=reverse)
            elif sort_by == "mp_name":
                feed_status_list.sort(key=lambda x: x.get("mp_name", ""), reverse=reverse)
            elif sort_by == "updated_at":
                feed_status_list.sort(key=lambda x: x.get("updated_at") or "", reverse=reverse)
        else:
            # 默认按更新时间降序
            feed_status_list.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
        
        return success_response({
            "list": feed_status_list,
            "total": total,
            "page": {
                "limit": limit,
                "offset": offset
            }
        })
        
    except Exception as e:
        print_error(f"获取公众号状态失败: {str(e)}")
        return error_response(code=500, message=str(e))


@router.get("/pending-allocations", summary="查看待认领的任务数量")
async def get_pending_allocations_count(
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    查看待认领的任务数量
    
    网关可以查看当前有多少任务等待子节点认领
    """
    from core.models.cascade_task_allocation import CascadeTaskAllocation
    
    session = DB.get_session()
    try:
        # 待认领任务（node_id 为空）
        pending_count = session.query(CascadeTaskAllocation).filter(
            CascadeTaskAllocation.node_id == None,
            CascadeTaskAllocation.status == 'pending'
        ).count()
        
        # 执行中任务
        executing_count = session.query(CascadeTaskAllocation).filter(
            CascadeTaskAllocation.status.in_(['claimed', 'executing'])
        ).count()
        
        # 今日完成任务
        from datetime import datetime, timedelta
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        completed_today = session.query(CascadeTaskAllocation).filter(
            CascadeTaskAllocation.status == 'completed',
            CascadeTaskAllocation.completed_at >= today_start
        ).count()
        
        # 今日失败任务
        failed_today = session.query(CascadeTaskAllocation).filter(
            CascadeTaskAllocation.status == 'failed',
            CascadeTaskAllocation.completed_at >= today_start
        ).count()
        
        # 在线节点数
        online_nodes = session.query(CascadeNode).filter(
            CascadeNode.node_type == 1,
            CascadeNode.status == 1,
            CascadeNode.is_active == True
        ).count()
        
        return success_response({
            "pending_tasks": pending_count,
            "executing_tasks": executing_count,
            "completed_today": completed_today,
            "failed_today": failed_today,
            "online_nodes": online_nodes
        })
        
    except Exception as e:
        return error_response(code=500, message=str(e))


from datetime import datetime
