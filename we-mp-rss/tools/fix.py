import copy
from core.models.article import Article

def sanitize_utf8(content: str) -> str:
    """清理字符串中的非法UTF-8字符"""
    if not content:
        return ""
    try:
        # 尝试编码为UTF-8，忽略错误
        if isinstance(content, str):
            # 先编码为bytes，再解码回str，忽略错误
            return content.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
        elif isinstance(content, bytes):
            return content.decode('utf-8', errors='ignore')
        return str(content)
    except Exception:
        return ""

def fix_html(content:str):
    if not content:
        return ""
    # 先清理编码问题
    content = sanitize_utf8(content)
    from core.content_format import format_content
    from tools.mdtools.md2html import convert_markdown_to_html
    from tools.htmltools import htmltools
    
    content = htmltools.clean_html(content,remove_attributes= [{'src': ''}],
                         remove_ids=['content_bottom_interaction','activity-name','meta_content',"js_article_bottom_bar","js_pc_weapp_code","js_novel_card","js_pc_qr_code"]
                         )
    if not content:
        return ""
    content=format_content(content,content_format='markdown')
    if not content:
        return ""
    content=convert_markdown_to_html(content)
    return content
def fix_article(article):
    art=article.to_dict()
    art['content']=fix_html(art.get('content') or "")
    return art
