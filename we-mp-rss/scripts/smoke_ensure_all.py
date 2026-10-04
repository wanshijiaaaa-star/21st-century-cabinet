# -*- coding: utf-8 -*-
"""按用户需求：对库中所有 MP_WXS_ 公众号执行未在书架自动添加。"""
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

import sqlite3
from core.wx.model.weread_mp import MpsWereadMP

con = sqlite3.connect("data/db.db")
cur = con.cursor()
cur.execute(
    "SELECT id, mp_name FROM feeds WHERE id LIKE 'MP_WXS_%' "
    "AND id != 'MP_WXS_FEATURED_ARTICLES'"
)
rows = cur.fetchall()
con.close()

wx = MpsWereadMP()
wx._load_weread_auth()
print(f"共 {len(rows)} 个公众号，Cookie len={len(wx._weread_cookies)} vid={wx._weread_vid}")
for book_id, name in rows:
    try:
        ok, detail = wx.ensure_mp_on_shelf(book_id, name)
        print(f"[{name}] {book_id} -> ok={ok} | {detail}")
    except Exception as e:
        print(f"[{name}] {book_id} -> EXC {e}")
    time.sleep(1)
