# -*- coding: utf-8 -*-
"""一次性迁移：把 articles 表里 WEREAD_ 前缀的公众号文章规范化为标准 MP_WXS_。

旧逻辑：前端书架采集以 ``WEREAD_{book_id}`` 作为 mp_id 入库，
导致 mp_id=WEREAD_MP_WXS_xxx、id=WEREAD_xxx-xxx_...，与 feeds 表
（MP_WXS_xxx）无法关联，前端列表/RSS 看不到文章。

用法：python scripts/fix_weread_mp_articles.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

from core.db import DB
from core.models.article import Article

PREFIX = "WEREAD_"


def main():
    session = DB.get_session()
    rows = session.query(Article).filter(
        (Article.mp_id.like("WEREAD%")) | (Article.id.like("WEREAD%"))
    ).all()
    fixed = 0
    for art in rows:
        old_mp_id, old_id = art.mp_id, art.id
        if art.mp_id and art.mp_id.startswith(PREFIX):
            art.mp_id = art.mp_id[len(PREFIX):]
        if art.id and art.id.startswith(PREFIX):
            art.id = art.id[len(PREFIX):]
        if art.mp_id != old_mp_id or art.id != old_id:
            print(f"[迁移] {old_mp_id or ''} | {old_id or ''}")
            print(f"   -> {art.mp_id or ''} | {art.id or ''}")
            session.add(art)
            fixed += 1
    if fixed:
        session.commit()
    session.close()
    print(f"共迁移 {fixed} 条")


if __name__ == "__main__":
    main()
