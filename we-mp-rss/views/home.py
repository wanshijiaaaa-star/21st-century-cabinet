from fastapi import APIRouter, Request, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse
from typing import Optional
from apis.tags import get_tags
from core.lax.template_parser import TemplateParser
from views.config import base
from core.cache import cache_view, clear_cache_pattern
from views.base import get_tags_view, get_mps_view

# 创建路由器
router = APIRouter(tags=["首页"])

@router.get("/home", response_class=HTMLResponse, summary="首页 - 显示所有标签")
async def home_view(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(12, ge=1, le=50, description="每页数量")
):
    """
    首页显示所有标签，支持分页
    """
    try:
        # 标签固定显示前12个
        tags_data = get_tags_view(1, 12)
        # 公众号支持分页
        mps_data = get_mps_view(page, limit)
        
        # 读取模板文件
        template_path = base.home_template
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # 生成分页URL
        has_prev = mps_data.get('has_prev', False)
        has_next = mps_data.get('has_next', False)
        prev_url = f"/views/home?page={page - 1}&limit={limit}" if has_prev else None
        next_url = f"/views/home?page={page + 1}&limit={limit}" if has_next else None
        
        data = {
            "site": base.site,
            "tags": tags_data,
            "mps": mps_data,
            "current_page": page,
            "total_pages": mps_data.get('total_pages', 1),
            "total_items": mps_data.get('total_items', 0),
            "has_prev": has_prev,
            "has_next": has_next,
            "prev_url": prev_url,
            "next_url": next_url,
            "item_name": "个公众号"
        }
        
        # 使用模板引擎渲染
        parser = TemplateParser(template_content, template_dir=base.public_dir)
        html_content = parser.render(data)
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        print(f"获取首页数据错误: {str(e)}")
        # 读取模板文件
        template_path = base.home_template
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        parser = TemplateParser(template_content, template_dir=base.public_dir)
        html_content = parser.render({
            "site": base.site,
            "error": f"加载数据时出现错误: {str(e)}",
            "breadcrumb": [{"name": "首页", "url": "/views/home"}]
        })
        
        return HTMLResponse(content=html_content)

