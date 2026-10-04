# -*- coding: utf-8 -*-
"""端到端验证：模拟刷新接口的采集流程（带 CallBack），确认新文章能入库"""
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.wx.model.weread_mp import MpsWereadMP, WereadMPAPIError
from core.db import DB

# 与 jobs.article.UpdateArticle 等效（避免导入 jobs 触发 PIL 依赖）
def UpdateArticle(art, check_exist=True):
    return DB.add_article(art, check_exist=check_exist)

MP_ID = "MP_WXS_1240574601"
MP_NAME = "央视新闻"


def count_db():
    from core.db import DB
    from core.models.article import Article

    session = DB.get_session()
    try:
        n = session.query(Article.id).filter(Article.mp_id == MP_ID).count()
        return n
    finally:
        session.close()


print("=== 第一次：应发现新文章并入库 ===")
before = count_db()
print("采集前库中文章数:", before)
wx = MpsWereadMP()
wx._load_weread_auth()
try:
    wx.get_Articles(
        MP_ID,
        Mps_id=MP_ID,
        Mps_title=MP_NAME,
        CallBack=UpdateArticle,
        MaxPage=1,
    )
    print("get_Articles 完成，本会话 articles:", len(wx.articles))
except WereadMPAPIError as e:
    print(f"采集异常 code={e.code} msg={e.message} retriable={e.retriable}")
    sys.exit(1)
after = count_db()
print(f"采集后库中文章数: {after}，新增 {after - before} 篇")

print("\n=== 第二次：应命中增量跳过（无新文章） ===")
wx2 = MpsWereadMP()
wx2._load_weread_auth()
try:
    wx2.get_Articles(
        MP_ID,
        Mps_id=MP_ID,
        Mps_title=MP_NAME,
        CallBack=UpdateArticle,
        MaxPage=1,
    )
    print("get_Articles 完成，本会话 articles:", len(wx2.articles))
except WereadMPAPIError as e:
    print(f"采集异常 code={e.code} msg={e.message} retriable={e.retriable}")
    sys.exit(1)
after2 = count_db()
print(f"再次采集后库中文章数: {after2}，新增 {after2 - after} 篇（应为 0）")
