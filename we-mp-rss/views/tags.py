from fastapi import APIRouter, Request, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse
from typing import Optional
import os
import json
from datetime import datetime

from core.db import DB
from core.models.tags import Tags
from core.models.feed import Feed
from core.models.article import Article
from core.lax.template_parser import TemplateParser
from views.config import base
from driver.wxarticle import Web
from core.cache import cache_view, clear_cache_pattern
# 创建路由器
router = APIRouter(tags=["标签"])

@router.get("/tags", response_class=HTMLResponse, summary="标签 - 显示所有标签")
async def tags_view(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(8, ge=1, le=20, description="每页数量")
):
    """
    首页显示所有标签，支持分页
    """
    session = DB.get_session()
    try:
        # 查询标签总数
        total = session.query(Tags).filter(Tags.status == 1).count()
        
        # 计算偏移量
        offset = (page - 1) * limit
        
        # 查询标签列表
        tags = session.query(Tags).filter(Tags.status == 1).order_by(Tags.created_at.desc()).offset(offset).limit(limit).all()
        
        # 处理标签数据
        tag_list = []
        for tag in tags:
            # 解析mps_id JSON
            mps_ids = []
            if tag.mps_id:
                try:
                    mps_data = json.loads(tag.mps_id)
                    mps_ids = [str(mp['id']) for mp in mps_data] if isinstance(mps_data, list) else []
                except (json.JSONDecodeError, TypeError):
                    mps_ids = []
            
            # 统计文章数量
            article_count = 0
            if mps_ids:
                article_count = session.query(Article).filter(
                    Article.mp_id.in_(mps_ids),
                    Article.status == 1
                ).count()
            
            # 获取关联的公众号数量
            mp_count = len(mps_ids) if mps_ids else 0
            
            tag_data = {
                "id": tag.id,
                "name": tag.name,
                "cover": Web.get_image_url(tag.cover) if tag.cover else "",
                "intro": tag.intro,
                "mp_count": mp_count,
                "article_count": article_count,
                "sync_time": datetime.fromtimestamp(tag.sync_time).strftime('%Y-%m-%d %H:%M') if tag.sync_time else "未同步",
                "created_at": tag.created_at.strftime('%Y-%m-%d') if tag.created_at else ""
            }
            tag_list.append(tag_data)
        
        # 计算分页信息
        total_pages = (total + limit - 1) // limit
        has_prev = page > 1
        has_next = page < total_pages
        
        # 构建面包屑
        breadcrumb = [
            {"name": "标签", "url": "/views/tags"}
        ]
        
        # 读取模板文件
        template_path = base.tags_template
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # 生成完整的分页URL
        prev_url = f"/views/tags?page={page - 1}&limit={limit}" if has_prev else None
        next_url = f"/views/tags?page={page + 1}&limit={limit}" if has_next else None
        
        # 使用模板引擎渲染
        parser = TemplateParser(template_content, template_dir=base.public_dir)
        render_context = {
            "site": base.site,
            "tags": tag_list,
            "current_page": page,
            "total_pages": total_pages,
            "total_items": total,
            "limit": limit,
            "has_prev": has_prev,
            "has_next": has_next,
            "prev_url": prev_url,
            "next_url": next_url,
            "breadcrumb": breadcrumb,
            "item_name": "个标签"
        }
        html_content = parser.render(render_context)
        
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
            "breadcrumb": [{"name": "标签", "url": "/views/tags"}]
        })
        
        return HTMLResponse(content=html_content)
    finally:
        session.close()


@router.get("/tag/{tag_id}", response_class=HTMLResponse, summary="标签详情页")
async def tag_detail_view(
    request: Request,
    tag_id: str,
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(8, ge=1, le=20, description="每页文章数量"),
    keyword: Optional[str] = Query(None, description="搜索关键字")
):
    """
    显示标签详情和关联的文章列表
    """
    session = DB.get_session()
    try:
        # 查询标签信息
        tag = session.query(Tags).filter(Tags.id == tag_id, Tags.status == 1).first()
        if not tag:
            raise HTTPException(status_code=404, detail="标签不存在")
        
        # 解析mps_id JSON
        mps_ids = []
        if tag.mps_id:
            try:
                mps_data = json.loads(tag.mps_id)
                mps_ids = [str(mp['id']) for mp in mps_data] if isinstance(mps_data, list) else []
            except (json.JSONDecodeError, TypeError):
                mps_ids = []
        
        # 获取关联的公众号信息
        mps_info = []
        if mps_ids:
            mps_info = session.query(Feed).filter(Feed.id.in_(mps_ids)).all()
        
        # 构建基础查询条件
        base_conditions = [
            Article.mp_id.in_(mps_ids),
            Article.status == 1
        ]
        
        # 添加关键字搜索条件
        if keyword and keyword.strip():
            search_term = f"%{keyword.strip()}%"
            base_conditions.append(Article.title.like(search_term))
        
        # 查询文章总数
        total = 0
        if mps_ids:
            total = session.query(Article).filter(*base_conditions).count()
        
        # 计算偏移量
        offset = (page - 1) * limit
        
        # 查询文章列表
        articles = []
        if mps_ids:
            articles_query = session.query(Article, Feed).join(
                Feed, Article.mp_id == Feed.id
            ).filter(*base_conditions).order_by(Article.publish_time.desc()).offset(offset).limit(limit).all()
            
            for article, feed in articles_query:
                article_data = {
                    "id": article.id,
                    "title": article.title,
                    "description": article.description or Web.get_description(article.content),
                    "pic_url": Web.get_image_url(article.pic_url),
                    "mp_cover": Web.get_image_url(feed.mp_cover) if feed else "",
                    "url": article.url,
                    "publish_time": datetime.fromtimestamp(article.publish_time).strftime('%Y-%m-%d %H:%M') if article.publish_time else "",
                    "mp_name": feed.mp_name if feed else "未知公众号",
                    "mp_id": article.mp_id
                }
                articles.append(article_data)
        
        # 处理标签数据
        tag_data = {
            "id": tag.id,
            "name": tag.name,
            "cover":tag.cover,
            "intro": tag.intro,
            "mp_count": len(mps_ids),
            "article_count": total,
            "sync_time": datetime.fromtimestamp(tag.sync_time).strftime('%Y-%m-%d %H:%M') if tag.sync_time else "未同步",
            "mps": [{"id": mp.id, "name": mp.mp_name, "cover": Web.get_image_url(mp.mp_cover)} for mp in mps_info]
        }
        
        # 计算分页信息
        total_pages = (total + limit - 1) // limit
        has_prev = page > 1
        has_next = page < total_pages
        
        # 构建面包屑
        breadcrumb = [
            {"name": tag.name, "url": None}
        ]
        
        # 生成完整的分页URL
        def build_tag_page_url(page_num: int) -> str:
            params = [f"page={page_num}", f"limit={limit}"]
            if keyword:
                params.append(f"keyword={keyword}")
            return f"/views/tag/{tag_id}?" + "&".join(params)
        
        prev_url = build_tag_page_url(page - 1) if has_prev else None
        next_url = build_tag_page_url(page + 1) if has_next else None
        
        # 读取模板文件
        template_path = base.tags_articles_template
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        parser = TemplateParser(template_content, template_dir=base.public_dir)
        html_content = parser.render({
            "site": base.site,
            "tag": tag_data,
            "articles": articles,
            "current_page": page,
            "total_pages": total_pages,
            "total_items": total,
            "limit": limit,
            "has_prev": has_prev,
            "has_next": has_next,
            "prev_url": prev_url,
            "next_url": next_url,
            "breadcrumb": breadcrumb,
            "item_name": "篇文章",
            "keyword": keyword
        })
        
        return HTMLResponse(content=html_content)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"获取标签详情错误: {str(e)}")
        # 读取模板文件
        template_path = base.tags_articles_template
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        parser = TemplateParser(template_content, template_dir=base.public_dir)
        html_content = parser.render({
            "site": base.site,
            "error": f"加载数据时出现错误: {str(e)}",
            "breadcrumb": [{"name": "首页", "url": "/views/home"}]
        })
        
        return HTMLResponse(content=html_content)
    finally:
        session.close()