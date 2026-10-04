from fastapi import APIRouter, Depends, HTTPException,Body,Path,Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from core.models.config_management import ConfigManagement
from core.db  import DB
from core.auth import get_current_user_or_ak
from .base import  success_response, error_response
from core.config import cfg
router = APIRouter(prefix="/configs", tags=["配置管理"])


@router.get("",summary="获取配置项列表")
def list_configs(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user_or_ak)
):
    # db=DB.get_session()
    """获取配置项列表"""
    try:
        # total = db.query(ConfigManagement).count()
        # configs = db.query(ConfigManagement).offset(offset).limit(limit).all()
        from core.yaml_db import YamlDB
        configs = YamlDB.store_config_to_list(cfg._config) 
        total=len(configs)
        return success_response(data={
            "list": configs,
            "page": {
                    "limit": limit,
                    "offset": offset
                },
                "total": total
        })
    except Exception as e:
        return error_response(code=500, message=str(e))

@router.get("/{config_key}", summary="获取单个配置项详情")
def get_config(
    config_key: str,
    current_user: dict = Depends(get_current_user_or_ak)
):
    db=DB.get_session()
    """获取单个配置项详情"""
    try:
        config = db.query(ConfigManagement).filter(ConfigManagement.config_key == config_key).first()
        if not config:
            raise HTTPException(status_code=404, detail="Config not found")
        return success_response(data=config)
    except Exception as e:
        return error_response(code=500, message=str(e))

class ConfigManagementCreate(BaseModel):
    config_key: str
    config_value: str
    description: Optional[str] = None

@router.post("", summary="创建配置项")
def create_config(
    config_data: ConfigManagementCreate = Body(...),
    current_user: dict = Depends(get_current_user_or_ak)
):
    db=DB.get_session()
    """创建配置项"""
    try:
        # 检查config_key是否已存在
        existing_config = db.query(ConfigManagement).filter(ConfigManagement.config_key == config_data.config_key).first()
        if existing_config:
            raise HTTPException(status_code=400, detail="Config with this key already exists")
        
        db_config = ConfigManagement(
            config_key=config_data.config_key,
            config_value=config_data.config_value,
            description=config_data.description
        )
        db.add(db_config)
        db.commit()
        db.refresh(db_config)
        return success_response(data=db_config)
    except Exception as e:
        db.rollback()
        return error_response(code=500, message=str(e))

@router.put("/{config_key}", summary="更新配置项")
def update_config(
    config_key: str=Path(...,min_length=1),
    config_data: ConfigManagementCreate = Body(...),
    current_user: dict = Depends(get_current_user_or_ak)
):
    db=DB.get_session()
    """更新配置项"""
    try:
        db_config = db.query(ConfigManagement).filter(ConfigManagement.config_key == config_key).first()
        if not db_config:
            raise HTTPException(status_code=404, detail="Config not found")
        
        if config_data.config_value is not None:
            db_config.config_value = config_data.config_value
        if config_data.description is not None:
            db_config.description = config_data.description
        
        db.commit()
        db.refresh(db_config)
        return success_response(data=db_config)
    except Exception as e:
        db.rollback()
        return error_response(code=500, message=str(e))

@router.delete("/{config_key}",summary="删除配置项")
def delete_config(
    config_key: str,
    current_user: dict = Depends(get_current_user_or_ak)
):
    db=DB.get_session()
    """删除配置项"""
    try:
        db_config = db.query(ConfigManagement).filter(ConfigManagement.config_key == config_key).first()
        if not db_config:
            raise HTTPException(status_code=404, detail="Config not found")
        
        db.delete(db_config)
        db.commit()
        return success_response(message="Config deleted successfully")
    except Exception as e:
        db.rollback()
        return error_response(code=500, message=str(e))