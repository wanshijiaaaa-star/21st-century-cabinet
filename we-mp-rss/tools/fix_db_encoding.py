"""
修复数据库中的UTF-8编码问题
运行方式: python -m tools.fix_db_encoding
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import DB
from core.models.article import Article
from tools.fix import sanitize_utf8
from sqlalchemy import text

def fix_articles_encoding():
    """修复 articles 表中的编码问题"""
    session = DB.get_session()
    
    # 使用原生SQL查询，逐行处理
    result = session.execute(text("SELECT id, content, content_html FROM articles"))
    
    fixed_count = 0
    error_count = 0
    
    for row in result:
        article_id = row[0]
        content = row[1]
        content_html = row[2]
        
        try:
            # 检查并修复编码
            clean_content = sanitize_utf8(content) if content else None
            clean_html = sanitize_utf8(content_html) if content_html else None
            
            # 如果内容有变化，更新数据库
            if clean_content != content or clean_html != content_html:
                session.execute(
                    text("UPDATE articles SET content = :content, content_html = :html WHERE id = :id"),
                    {"content": clean_content, "html": clean_html, "id": article_id}
                )
                fixed_count += 1
                print(f"已修复: {article_id}")
        except Exception as e:
            error_count += 1
            print(f"处理 {article_id} 时出错: {e}")
    
    session.commit()
    print(f"\n修复完成: 成功 {fixed_count} 条，失败 {error_count} 条")

if __name__ == "__main__":
    print("开始修复数据库编码问题...")
    fix_articles_encoding()
