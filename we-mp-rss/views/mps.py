from fastapi import APIRouter, Request, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse
from typing import Optional
import os
from core.db import DB
from core.lax.template_parser import TemplateParser
from views.config import base
from core.cache import cache_view, clear_cache_pattern
from views.base import get_mps_view
# 创建路由器
router = APIRouter(tags=["公众号"])

@router.get("/mps", response_class=HTMLResponse, summary="公众号 - 显示所有公众号")
async def mps_view(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(8, ge=1, le=20, description="每页数量")
):
    """
    首页显示所有公众号，支持分页
    """
    try:
        data = get_mps_view(page, limit)
        # 读取模板文件
        template_path = base.mps_template
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()

        data['site'] = base.site
        # 生成完整的分页URL
        has_prev = data.get('has_prev', False)
        has_next = data.get('has_next', False)
        prev_page = page - 1 if has_prev else page
        next_page = page + 1 if has_next else page
        data['prev_url'] = f"/views/mps?page={prev_page}&limit={limit}" if has_prev else None
        data['next_url'] = f"/views/mps?page={next_page}&limit={limit}" if has_next else None
        data['item_name'] = '个公众号'

        # 使用模板引擎渲染
        parser = TemplateParser(template_content, template_dir=base.public_dir)
        html_content = parser.render(data)
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        print(f"获取首页数据错误: {str(e)}")
        # 读取模板文件
        template_path = base.mps_template
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        parser = TemplateParser(template_content, template_dir=base.public_dir)
        html_content = parser.render({
            "site": base.site,
            "error": f"加载数据时出现错误: {str(e)}",
            "breadcrumb": [{"name": "公众号", "url": "/views/mps"}]
        })
        
        return HTMLResponse(content=html_content)
   