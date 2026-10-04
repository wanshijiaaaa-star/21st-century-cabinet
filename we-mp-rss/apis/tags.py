from fastapi import APIRouter, Depends, HTTPException,status
from typing import List
from datetime import datetime
from core.models.tags import Tags as TagsModel
from core.database import get_db
from sqlalchemy.orm import Session
from schemas.tags import Tags, TagsCreate
from .base import success_response, error_response
from core.auth import get_current_user_or_ak
from core.cache import clear_cache_pattern

# 标签管理API路由
# 提供标签的增删改查功能
# 需要管理员权限执行写操作
router = APIRouter(prefix="/tags", tags=["标签管理"])

@router.get("", 
    summary="获取标签列表",
    description="分页获取所有标签信息")
async def get_tags(offset: int = 0, limit: int = 100, db: Session = Depends(get_db),cur_user: dict = Depends(get_current_user_or_ak)):
    """
    获取标签列表
    
    参数:
    - offset: 跳过记录数，用于分页
    - limit: 每页记录数，默认100
    
    返回:
    - 包含标签列表和分页信息的成功响应
    """
    query = db.query(TagsModel)
    total = query.count()
    tags = query.offset(offset).limit(limit).all()
    return success_response(data={
        "list": tags,
        "page": {
            "limit": limit,
            "offset": offset,
            "total": total
        },
        "total": total
    })

@router.post("",
    summary="创建新标签",
    description="创建一个新的标签"
   )
async def create_tag(tag: TagsCreate, db: Session = Depends(get_db),cur_user: dict = Depends(get_current_user_or_ak)):
    """
    创建新标签
    
    参数:
    - tag: TagsCreate模型，包含标签信息
    
    请求体示例:
    {
        "name": "新标签",
        "cover": "http://example.com/cover.jpg",
        "intro": "新标签的描述",
        "status": 1
    }
    
    返回:
    - 成功: 包含新建标签信息的响应
    - 失败: 错误响应
    """
    import uuid
    try:
        db_tag = TagsModel(
            id=str(uuid.uuid4()),
            name=tag.name or '',
            cover=tag.cover or '',
            intro=tag.intro or '',
            mps_id =tag.mps_id,
            status=tag.status,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(db_tag)
        db.commit()
        db.refresh(db_tag)
        
        # 清除相关缓存
        clear_cache_pattern("home_page")
        clear_cache_pattern("tag_detail")
        
        return success_response(data=db_tag)
    except Exception as e:
         from core.print  import print_error
         print_error(e)
         raise HTTPException(
            status_code=status.HTTP_201_CREATED,
            detail=error_response(
                code=50001,
                message=f"暂无数据",
            )
        )

@router.get("/{tag_id}", summary="获取单个标签详情",  description="根据标签ID获取标签详细信息")
async def get_tag(tag_id: str, db: Session = Depends(get_db),cur_user: dict = Depends(get_current_user_or_ak)):
    """
    获取单个标签详情
    
    参数:
    - tag_id: 标签ID
    
    返回:
    - 成功: 包含标签详情的响应
    - 失败: 201错误响应(标签不存在)
    """
    tag = db.query(TagsModel).filter(TagsModel.id == tag_id).first()
    if not tag:
        return error_response(code=status.HTTP_201_CREATED, message="Tag not found")
    return success_response(data=tag)

@router.put("/{tag_id}",
    summary="更新标签信息",
    description="根据标签ID更新标签信息",
 )
async def update_tag(tag_id: str, tag_data: TagsCreate, db: Session = Depends(get_db),cur_user: dict = Depends(get_current_user_or_ak)):
    """
    更新标签信息
    
    参数:
    - tag_id: 要更新的标签ID
    - tag_data: TagsCreate模型，包含要更新的标签信息
    
    请求体示例:
    {
        "name": "更新后的标签",
        "cover": "http://example.com/new_cover.jpg",
        "intro": "更新后的描述",
        "status": 1
    }
    
    返回:
    - 成功: 包含更新后标签信息的响应
    - 失败: 404错误响应(标签不存在)或500错误响应(服务器错误)
    """
    try:
        tag = db.query(TagsModel).filter(TagsModel.id == tag_id).first()
        if not tag:
            return error_response(code=404, message="Tag not found")
        
        tag.name = tag_data.name
        tag.cover = tag_data.cover
        tag.intro = tag_data.intro
        tag.status = tag_data.status
        tag.mps_id = tag_data.mps_id
        tag.updated_at = datetime.now()
        
        db.commit()
        db.refresh(tag)
        
        # 清除相关缓存
        clear_cache_pattern("home_page")
        clear_cache_pattern("tag_detail")
        
        return success_response(data=tag)
    except Exception as e:
        return error_response(code=500, message=str(e))

@router.delete("/{tag_id}",
    summary="删除标签",
    description="根据标签ID删除标签",
   )
async def delete_tag(tag_id: str, db: Session = Depends(get_db),cur_user: dict = Depends(get_current_user_or_ak)):
    """
    删除标签
    
    参数:
    - tag_id: 要删除的标签ID
    
    返回:
    - 成功: 删除成功的响应
    - 失败: 404错误响应(标签不存在)或500错误响应(服务器错误)
    """
    try:
        tag = db.query(TagsModel).filter(TagsModel.id == tag_id).first()
        if not tag:
            return error_response(code=status.HTTP_201_CREATED, message="Tag not found")
        db.delete(tag)
        db.commit()
        
        # 清除相关缓存
        clear_cache_pattern("home_page")
        clear_cache_pattern("tag_detail")
        
        return success_response(message="Tag deleted successfully")
    except Exception as e:
        return error_response(code=status.HTTP_201_CREATED, message=str(e))