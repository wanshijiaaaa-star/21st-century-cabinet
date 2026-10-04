from fastapi import APIRouter, Request, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse
from typing import Optional
import os
import views.config as config
# 创建路由器
router = APIRouter(prefix="/views", tags=["网页预览"])

from .home import router as home_router
from .articles import router as articles_router
from .tags import router as tags_router
from .mps import router as mps_router
from .article_detail import router as article_detail_router

# 注册子路由
router.include_router(home_router)
router.include_router(articles_router)
router.include_router(article_detail_router)
router.include_router(tags_router)
router.include_router(mps_router)