from fastapi import APIRouter, Request, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse
from typing import Optional
import os
from datetime import datetime
import re
import json
from views.base import process_content_images, _render_template_with_error
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
router = APIRouter(tags=["文章详情"])
@router.get("/print/{article_id}", response_class=HTMLResponse, summary="文章打印页")
@cache_view("article_print", ttl=1)  
async def print_article(
    request: Request,
    article_id: str,
):
    return await article_detail_view(request, article_id, isprint=True)

@router.get("/article/{article_id}", response_class=HTMLResponse, summary="文章详情页")
@cache_view("article_detail", ttl=1)  # 缓存1小时
async def article_detail_view(
    request: Request,
    article_id: str,
    isprint:bool=False
):
    """
    文章详情页面
    """
    session = DB.get_session()
    try:
        # 查询文章信息
        article_query = session.query(Article, Feed).join(
            Feed, Article.mp_id == Feed.id
        ).filter(Article.id == article_id, Article.status == 1, Feed.status == 1).first()
        
        
        if not article_query:
            raise HTTPException(status_code=404, detail="文章不存在")
        
        if len(article_query) != 2:
            raise HTTPException(status_code=500, detail="数据查询错误")
        article, feed = article_query
        
        # 标记为已读（可选）
        # if not article.is_read:
        #     article.is_read = 1
        #     session.commit()
        
        # 获取相关文章（同公众号的其他文章，排除大字段）
        related_articles = session.query(Article).options(
            defer(Article.content),      # type: ignore
            defer(Article.content_html)  # type: ignore
        ).filter(
            Article.mp_id == article.mp_id,
            Article.id != article_id,
            Article.status == 1
        ).order_by(Article.publish_time.desc()).limit(5).all()
        
        # 获取上一个和下一个文章ID（排除大字段）
        prev_article = session.query(Article.id, Article.title).filter(
            Article.mp_id == article.mp_id,
            Article.publish_time < article.publish_time,
            Article.status == 1
        ).order_by(Article.publish_time.desc()).first()
        
        next_article = session.query(Article.id, Article.title).filter(
            Article.mp_id == article.mp_id,
            Article.publish_time > article.publish_time,
            Article.status == 1
        ).order_by(Article.publish_time.asc()).first()
        
        related_list = []
        for rel_article in related_articles:
            rel_data = {
                "id": rel_article.id,
                "title": rel_article.title,
                "description": rel_article.description or Web.get_description(rel_article.content),
                "pic_url": Web.get_image_url(rel_article.pic_url),
                "publish_time": datetime.fromtimestamp(rel_article.publish_time).strftime('%Y-%m-%d %H:%M') if rel_article.publish_time else ""
            }
            related_list.append(rel_data)
        
        # 处理文章数据
        # 处理文章内容中的图片链接
        raw_content = article.content
        processed_content = process_content_images(raw_content)
        
        # 根据 show_type 获取类型名称
        show_type_map = {
            0: "图文",
            5: "视频",
            7: "音频",
            10: "贴图",
            11: "分享"
        }
        show_type_name = show_type_map.get(article.show_type, f"其他({article.show_type})" if article.show_type is not None else "未设置")
        
        article_data = {
            "id": article.id,
            "title": article.title,
            "description": article.description or Web.get_description(article.content),
            "pic_url": article.pic_url,
            "url": article.url,
            "show_type": article.show_type,
            "show_type_name": show_type_name,
            "publish_time": datetime.fromtimestamp(article.publish_time).strftime('%Y-%m-%d %H:%M') if article.publish_time else "",
            "created_at": article.created_at.strftime('%Y-%m-%d %H:%M') if article.created_at else "",
            "content": processed_content,
            "mp_name": feed.mp_name if feed else "未知公众号",
            "mp_id": article.mp_id,
            "mp_cover": feed.mp_cover if feed else "/static/logo.png",
            "mp_intro": feed.mp_intro if feed else "",
        }
        
        # 构建面包屑
        breadcrumb = [
            {"name": feed.mp_name, "url": f"/views/articles?mp_id={article_data['mp_id']}"},
            {"name": article_data["title"][:50] + "..." if len(article_data["title"]) > 50 else article_data["title"], "url": None}
        ]
        
        # 读取模板文件
        if isprint:
            template_path = base.article_detail_print_template
        else:
            template_path = base.article_detail_template
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        parser = TemplateParser(template_content, template_dir=base.public_dir)
        html_content = parser.render({
            "site": base.site,
            "article": article_data,
            "related_articles": related_list,
            "prev_article": {"id": prev_article[0], "title": prev_article[1]} if prev_article else "",
            "next_article": {"id": next_article[0], "title": next_article[1]} if next_article else "",
            "breadcrumb": breadcrumb,
        })
        
        return HTMLResponse(content=html_content)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"获取文章详情错误: {str(e)}")
        return _render_template_with_error(
            base.article_detail_template,
            f"加载文章时出现错误: {str(e)}",
            [{"name": "首页", "url": "/views/home"}, {"name": "文章列表", "url": "/views/articles"}]
        )
    finally:
        session.close()