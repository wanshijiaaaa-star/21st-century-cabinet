"""环境异常统计API"""
from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime
from core.auth import get_current_user_or_ak
from .base import success_response, error_response
from core.redis_client import get_env_exception_stats

router = APIRouter(prefix="/env-exception", tags=["环境异常统计"])


@router.get("/stats", summary="获取环境异常统计", description="获取指定日期的环境异常统计信息")
async def get_stats(
    date: Optional[str] = Query(
        None, 
        description="日期，格式为 YYYY-MM-DD，默认为今天",
        regex=r"^\d{4}-\d{2}-\d{2}$"
    ),
    current_user: dict = Depends(get_current_user_or_ak)
):
    """获取环境异常统计信息
    
    Args:
        date: 日期，格式为 YYYY-MM-DD
        
    Returns:
        统计信息，包含：
        - total: 当日总异常次数
        - urls: 异常URL列表
        - mp_stats: 公众号维度统计
        - recent_logs: 最近异常日志
    """
    try:
        stats = get_env_exception_stats(date)
        
        if "error" in stats:
            return error_response(
                code=500,
                message=stats["error"]
            )
            
        return success_response(stats)
        
    except Exception as e:
        return error_response(
            code=500,
            message=f"获取统计信息失败: {str(e)}"
        )


@router.get("/today", summary="获取今日环境异常统计", description="获取今天的环境异常统计信息")
async def get_today_stats(current_user: dict = Depends(get_current_user_or_ak)):
    """获取今日环境异常统计信息"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        stats = get_env_exception_stats(today)
        
        if "error" in stats:
            return error_response(
                code=500,
                message=stats["error"]
            )
            
        return success_response(stats)
        
    except Exception as e:
        return error_response(
            code=500,
            message=f"获取统计信息失败: {str(e)}"
        )
