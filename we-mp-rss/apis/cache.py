from fastapi import APIRouter, Depends, HTTPException, status
from core.auth import get_current_user_or_ak
from .base import success_response, error_response
from core.cache import clear_cache_pattern, clear_all_cache

router = APIRouter(prefix="/cache", tags=["缓存管理"])

@router.delete("/clear", summary="清除所有视图缓存", description="清除所有视图页面的缓存")
async def clear_all_view_cache(
    current_user: dict = Depends(get_current_user_or_ak)
):
    """清除所有视图缓存"""
    try:
        success = clear_all_cache()
        if success:
            return success_response({
                "message": "所有视图缓存已清除"
            })
        else:
            return error_response(
                code=500,
                message="清除缓存失败"
            )
    except Exception as e:
        return error_response(
            code=500,
            message=f"清除缓存时发生错误: {str(e)}"
        )

@router.delete("/clear/{pattern}", summary="清除指定模式的缓存", description="清除匹配指定模式的缓存")
async def clear_pattern_cache(
    pattern: str,
    current_user: dict = Depends(get_current_user_or_ak)
):
    """清除匹配模式的缓存"""
    try:
        success = clear_cache_pattern(pattern)
        if success:
            return success_response({
                "message": f"已清除模式为 '{pattern}' 的缓存"
            })
        else:
            return error_response(
                code=500,
                message="清除缓存失败"
            )
    except Exception as e:
        return error_response(
            code=500,
            message=f"清除缓存时发生错误: {str(e)}"
        )