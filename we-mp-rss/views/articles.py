from fastapi import APIRouter, Request, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse
from typing import Optional
import os
from datetime import datetime
import re
import json
from views.base import _render_template_with_error
from core.db import DB
from core.models.article import Article
from core.models.feed import Feed
from core.models.tags import Tags
from apis.base import format_search_kw
from core.lax.template_parser import TemplateParser
from views.config import base
from driver.wxarticle import Web
from core.cache import cache_view, clear_cache_pattern, data_cache
from sqlalchemy.orm import defer



# 创建路由器
router = APIRouter(tags=["文章"])

@router.get("/articles", response_class=HTMLResponse, summary="文章列表页")
async def articles_view(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(5, ge=1, le=20, description="每页数量"),
    mp_id: Optional[str] = Query(None, description="公众号ID筛选"),
    tag_id: Optional[str] = Query(None, description="标签ID筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    sort: str = Query("publish_time", description="排序方式: publish_time, created_at"),
    order: str = Query("desc", description="排序顺序: asc, desc"),
    has_content: Optional[str] = Query(None, description="只显示有正文的文章: 1/空")
):
    """
    文章列表页面，支持筛选、搜索和排序
    """
    session = DB.get_session()
    try:
        # 验证排序参数
        valid_sort_fields = {"publish_time", "created_at"}
        valid_orders = {"asc", "desc"}
        
        if sort not in valid_sort_fields:
            sort = "publish_time"
        if order not in valid_orders:
            order = "desc"
        
        # 预处理标签筛选的mp_ids
        mps_ids = []
        if tag_id:
            tag = session.query(Tags.mps_id).filter(Tags.id == tag_id, Tags.status == 1).scalar()
            if tag:
                try:
                    mps_data = json.loads(tag)
                    mps_ids = [str(mp['id']) for mp in mps_data] if isinstance(mps_data, list) else []
                except (json.JSONDecodeError, TypeError):
                    mps_ids = []
        
        # 构建基础查询条件
        base_conditions = [Article.status == 1]
        if mp_id:
            base_conditions.append(Article.mp_id == mp_id)
        if mps_ids:
            base_conditions.append(Article.mp_id.in_(mps_ids))
        if keyword and keyword.strip():
            search_filter = format_search_kw(keyword.strip())
            if search_filter is not None:
                base_conditions.append(search_filter)
        # 只显示有正文的文章
        if has_content == "1":
            base_conditions.append(Article.content.isnot(None))
            base_conditions.append(Article.content != "")
        
        # 使用单一查询获取文章和Feed信息
        from sqlalchemy import and_
        
        # 构建排序
        if sort == "publish_time":
            order_clause = Article.publish_time.desc() if order == "desc" else Article.publish_time.asc()
        else:  # created_at
            order_clause = Article.created_at.desc() if order == "desc" else Article.created_at.asc()
        
        # 主查询：一次性获取文章和Feed信息（排除大字段 content 和 content_html）
        query = session.query(Article, Feed).join(
            Feed, Article.mp_id == Feed.id, isouter=True
        ).options(
            defer(Article.content),      # type: ignore
            defer(Article.content_html)  # type: ignore
        ).filter(and_(*base_conditions)).order_by(order_clause)
        
        # 获取总数
        total = query.count()
        
        # 分页查询
        offset = (page - 1) * limit
        articles_data = query.offset(offset).limit(limit).all()
        
        # 处理文章数据
        article_list = []
        feed_dict = {}  # 用于后续筛选信息
        
        for article, feed in articles_data:
            if feed:
                feed_dict[feed.id] = feed
            
            article_data = {
                "id": article.id,
                "title": article.title,
                "description": article.description or Web.get_description(article.content),
                "pic_url": Web.get_image_url(article.pic_url),
                "url": article.url,
                "publish_time": datetime.fromtimestamp(article.publish_time).strftime('%Y-%m-%d %H:%M') if article.publish_time else "",
                "created_at": article.created_at.strftime('%Y-%m-%d %H:%M') if article.created_at else "",
                "mp_name": feed.mp_name if feed else "未知公众号",
                "mp_id": article.mp_id,
                "mp_cover": Web.get_image_url(feed.mp_cover) if feed else "",
                "is_read": bool(article.is_read),
            }
            article_list.append(article_data)
        
        # 获取筛选信息
        filter_info = {}
        if mp_id and mp_id in feed_dict:
            feed = feed_dict[mp_id]
            filter_info["mp"] = {"id": feed.id, "name": feed.mp_name}
        
        if tag_id:
            tag = session.query(Tags.id, Tags.name).filter(Tags.id == tag_id).first()
            if tag:
                filter_info["tag"] = {"id": tag.id, "name": tag.name}
        
        # 获取标签和热门公众号信息（使用缓存）
        from core.cache import data_cache
        
        # 尝试从缓存获取标签选项
        cache_key_tags = "tag_options_all"
        tag_options = data_cache.get(cache_key_tags)
        if tag_options is None:
            tags = session.query(Tags.id, Tags.name).filter(Tags.status == 1).order_by(Tags.name).all()
            tag_options = [{"id": tag.id, "name": tag.name} for tag in tags]
            data_cache.set(cache_key_tags, tag_options)  # 使用默认TTL（1小时）
        
        # 尝试从缓存获取热门公众号
        cache_key_popular = "popular_mps_top10"
        mp_options = data_cache.get(cache_key_popular)
        if mp_options is None:
            from sqlalchemy import func
            
            popular_mps = session.query(
                Feed.id, Feed.mp_name,
                func.count(Article.id).label('article_count')
            ).join(
                Article, Feed.id == Article.mp_id
            ).filter(
                Article.status == 1,
                Feed.status == 1
            ).group_by(
                Feed.id, Feed.mp_name
            ).order_by(
                func.count(Article.id).desc()
            ).limit(10).all()
            
            mp_options = [{"id": str(row[0]), "name": row[1]} for row in popular_mps]
            data_cache.set(cache_key_popular, mp_options)  # 使用默认TTL（1小时）
        
        # 计算分页信息
        total_pages = (total + limit - 1) // limit
        has_prev = page > 1
        has_next = page < total_pages
        prev_page = page - 1 if has_prev else None
        next_page = page + 1 if has_next else None

        # 构建面包屑
        breadcrumb = [{"name": "文章列表", "url": "/views/articles"}]
        
        # 读取模板文件
        template_path = base.articles_template
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        feed_info = feed_dict.get(mp_id) if mp_id else None
        info = {
            "mp_name": feed_info.mp_name if feed_info else "",
            "mp_cover": Web.get_image_url(feed_info.mp_cover) if feed_info else "",
            "mp_intro": feed_info.mp_intro if feed_info else "",
            "mp_id": mp_id,
        } if feed_info else {}
        
        # 构建分页URL辅助函数
        def build_page_url(page_num: int) -> str:
            params = []
            if mp_id:
                params.append(f"mp_id={mp_id}")
            if tag_id:
                params.append(f"tag_id={tag_id}")
            if keyword:
                params.append(f"keyword={keyword}")
            if sort != "publish_time":
                params.append(f"sort={sort}")
            if order != "desc":
                params.append(f"order={order}")
            if has_content == "1":
                params.append(f"has_content={has_content}")
            params.append(f"page={page_num}")
            params.append(f"limit={limit}")
            return "/views/articles?" + "&".join(params)
        
        prev_url = build_page_url(prev_page) if has_prev else None
        next_url = build_page_url(next_page) if has_next else None
        
        parser = TemplateParser(template_content, template_dir=base.public_dir)
        html_content = parser.render({
            "site": base.site,
            "articles": article_list,
            "current_page": page,
            "total_pages": total_pages,
            "total_items": total,
            "limit": limit,
            "has_prev": has_prev,
            "has_next": has_next,
            "prev_page": prev_page,
            "next_page": next_page,
            "prev_url": prev_url,
            "next_url": next_url,
            "filter_info": filter_info,
            "tag_options": tag_options,
            "mp_options": mp_options,
            "info": info,
            "current_filters": {
                "mp_id": mp_id,
                "tag_id": tag_id,
                "keyword": keyword,
                "sort": sort,
                "order": order,
                "has_content": has_content
            },
            "breadcrumb": breadcrumb
        })
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        print(f"获取文章列表错误: {str(e)}")
        return _render_template_with_error(
            base.articles_template,
            f"加载数据时出现错误: {str(e)}",
            [{"name": "文章列表", "url": "/views/articles"}]
        )
    finally:
        session.close()
