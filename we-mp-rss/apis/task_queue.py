"""任务队列管理API"""
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from typing import Optional
from core.auth import get_current_user_or_ak
from core.queue import TaskQueue, ContentTaskQueue, get_all_queues_status
from core.task.task import TaskScheduler
from core.ws_manager import ws_manager
from .base import success_response, error_response
from core.log import logger
import asyncio

router = APIRouter(prefix="/task-queue", tags=["任务队列"])

@router.get("/status", summary="获取任务队列状态")
async def get_queue_status(
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    获取所有任务队列的详细状态信息
    
    返回:
        - main_queue: 主队列（文章采集）状态
        - content_queue: 内容补抓队列状态
    """
    try:
        status = get_all_queues_status()
        return success_response(data=status)
    except Exception as e:
        logger.error(f"Get queue status error: {str(e)}")
        return error_response(code=500, message=str(e))

@router.get("/main/status", summary="获取主队列状态")
async def get_main_queue_status(
    current_user: dict = Depends(get_current_user_or_ak)
):
    """获取主队列（文章采集）状态"""
    try:
        status = TaskQueue.get_detailed_status()
        return success_response(data=status)
    except Exception as e:
        logger.error(f"Get main queue status error: {str(e)}")
        return error_response(code=500, message=str(e))

@router.get("/content/status", summary="获取内容补抓队列状态")
async def get_content_queue_status(
    current_user: dict = Depends(get_current_user_or_ak)
):
    """获取内容补抓队列状态"""
    try:
        status = ContentTaskQueue.get_detailed_status()
        return success_response(data=status)
    except Exception as e:
        logger.error(f"Get content queue status error: {str(e)}")
        return error_response(code=500, message=str(e))

@router.get("/history", summary="获取任务执行历史")
async def get_queue_history(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    queue_type: str = Query("main", description="队列类型: main 或 content"),
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    获取任务执行历史记录（分页）
    
    参数:
        page: 页码，从1开始
        page_size: 每页数量，默认10条
        queue_type: 队列类型，main（主队列）或 content（内容补抓队列）
    """
    try:
        queue = ContentTaskQueue if queue_type == "content" else TaskQueue
        result = queue._get_history_page_from_redis(page, page_size)
        return success_response(data=result)
    except Exception as e:
        return error_response(code=500, message=str(e))

@router.post("/clear", summary="清空任务队列")
async def clear_queue(
    queue_type: str = Query("main", description="队列类型: main 或 content"),
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    清空任务队列中的所有待执行任务
    
    参数:
        queue_type: 队列类型，main（主队列）或 content（内容补抓队列）
    
    注意: 正在执行的任务不会被中断
    """
    try:
        queue = ContentTaskQueue if queue_type == "content" else TaskQueue
        queue.clear_queue()
        return success_response(message="队列已清空")
    except Exception as e:
        return error_response(code=500, message=str(e))

@router.post("/history/clear", summary="清空任务历史")
async def clear_history(
    queue_type: str = Query("main", description="队列类型: main 或 content"),
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    清空任务执行历史记录
    
    参数:
        queue_type: 队列类型，main（主队列）或 content（内容补抓队列）
    """
    try:
        queue = ContentTaskQueue if queue_type == "content" else TaskQueue
        queue.clear_history()
        return success_response(message="任务历史已清空")
    except Exception as e:
        return error_response(code=500, message=str(e))

@router.get("/scheduler/status", summary="获取调度器状态")
async def get_scheduler_status(
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    获取定时任务调度器的状态信息
    
    返回:
        - running: 调度器是否运行中
        - job_count: 定时任务数量
        - next_run_times: 各任务下次执行时间
    """
    try:
        # 从 jobs.mps 导入调度器实例
        from jobs.mps import scheduler
        status = scheduler.get_scheduler_status()
        logger.info(f"Scheduler status: {status}")
        return success_response(data=status)
    except ImportError as e:
        logger.error(f"Import scheduler error: {str(e)}")
        return success_response(data={
            'running': False,
            'job_count': 0,
            'next_run_times': []
        })
    except Exception as e:
        logger.error(f"Get scheduler status error: {str(e)}")
        return error_response(code=500, message=str(e))

@router.get("/scheduler/jobs", summary="获取定时任务列表")
async def get_scheduler_jobs(
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    获取所有定时任务的详细信息
    """
    try:
        from jobs.mps import scheduler
        job_ids = scheduler.get_job_ids()
        jobs = []
        for job_id in job_ids:
            try:
                details = scheduler.get_job_details(job_id)
                jobs.append(details)
            except Exception as job_error:
                logger.warning(f"Get job {job_id} details error: {str(job_error)}")
                jobs.append({'id': job_id, 'error': '获取详情失败'})
        logger.info(f"Scheduler jobs: {len(jobs)} jobs")
        return success_response(data={
            'jobs': jobs,
            'total': len(jobs)
        })
    except ImportError as e:
        logger.error(f"Import scheduler error: {str(e)}")
        return success_response(data={
            'jobs': [],
            'total': 0
        })
    except Exception as e:
        logger.error(f"Get scheduler jobs error: {str(e)}")
        return error_response(code=500, message=str(e))


@router.websocket("/ws")
async def queue_websocket(websocket: WebSocket, token: Optional[str] = None):
    """
    WebSocket 端点，实时推送队列状态更新
    
    参数:
        token: JWT 认证令牌（通过查询参数传递）
    
    消息格式:
    {
        "type": "queue_status",
        "data": {
            "main_queue": { ... 主队列状态 ... },
            "content_queue": { ... 内容队列状态 ... }
        }
    }
    """
    logger.info(f"[WebSocket] 收到连接请求, token存在: {bool(token)}")
    
    # 验证 token
    if not token:
        logger.warning("[WebSocket] 未提供认证令牌")
        await websocket.close(code=4001, reason="未提供认证令牌")
        return
    
    try:
        import jwt
        from core.auth import SECRET_KEY, ALGORITHM, get_user
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            await websocket.close(code=4001, reason="无效的令牌")
            return
        
        user = get_user(username)
        if not user:
            await websocket.close(code=4001, reason="用户不存在")
            return
        
        logger.info(f"[WebSocket] 用户 {username} 认证成功")
    except jwt.ExpiredSignatureError:
        logger.warning("[WebSocket] 令牌已过期")
        await websocket.close(code=4001, reason="令牌已过期")
        return
    except jwt.PyJWTError as e:
        logger.warning(f"WebSocket 认证失败: {e}")
        await websocket.close(code=4001, reason="认证失败")
        return
    except Exception as e:
        logger.error(f"WebSocket 认证异常: {e}")
        await websocket.close(code=4001, reason="认证异常")
        return
    
    await ws_manager.connect(websocket)
    logger.info(f"[WebSocket] 连接已建立，当前连接数: {ws_manager.connection_count}")
    
    try:
        # 立即发送当前状态（所有队列）
        status = get_all_queues_status()
        await websocket.send_json({
            "type": "queue_status",
            "data": status
        })
        
        # 保持连接，定期推送状态（每10秒作为兜底，主要依靠实时推送）
        while True:
            await asyncio.sleep(10)
            status = get_all_queues_status()
            await websocket.send_json({
                "type": "queue_status",
                "data": status
            })
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info(f"[WebSocket] 客户端断开连接，当前连接数: {ws_manager.connection_count}")
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")
        ws_manager.disconnect(websocket)


async def broadcast_queue_status():
    """广播队列状态到所有 WebSocket 连接"""
    status = get_all_queues_status()
    await ws_manager.broadcast({
        "type": "queue_status",
        "data": status
    })


def broadcast_queue_status_sync():
    """同步版本：广播队列状态"""
    status = get_all_queues_status()
    ws_manager.broadcast_sync({
        "type": "queue_status",
        "data": status
    })
