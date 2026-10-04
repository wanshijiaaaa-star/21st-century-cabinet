# -*- coding: utf-8 -*-
"""实测改造后的 weread_mp cover 增量采集链路（用 feeds 表真实公众号）"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

from core.db import DB
from core.models.feed import Feed
from core.wx.model.weread_mp import MpsWereadMP, WereadMPAPIError, build_mp_link_from_review_id


def pick_feed() -> tuple:
    """取 feeds 表中第一个非精选的 MP_WXS_ 公众号"""
    session = DB.get_session()
    try:
        row = (
            session.query(Feed.id, Feed.mp_name)
            .filter(Feed.id.like("MP_WXS_%"))
            .filter(Feed.id != "MP_WXS_FEATURED_ARTICLES")
            .first()
        )
        return (row[0], row[1]) if row else ("", "")
    finally:
        session.close()


def callback(art: dict):
    from core.db import DB

    ok = DB.add_article(art)  # 与 jobs.article.UpdateArticle 相同的真实入库逻辑
    print(f"  >> add_article 返回={ok} title={art.get('title')!r}")
    print(f"     url={art.get('url')} | content_len={len(art.get('content') or '')}")
    return ok


def main():
    mp_id, mp_name = pick_feed()
    if not mp_id:
        print("feeds 表中没有可用的 MP_WXS_ 公众号")
        return
    print(f"测试公众号: {mp_id} ({mp_name})")

    wx = MpsWereadMP()
    wx._load_weread_auth()
    print("cookie 前 40 字符:", (wx._weread_cookies or "")[:40], "..." if wx._weread_cookies else "(空)")

    # 1) cover 链路
    cover = wx._get_mp_cover(mp_id)
    rid = cover.get("reviewId", "")
    print("\n[cover] name:", cover.get("name"))
    print("[cover] title:", cover.get("title"))
    print("[cover] reviewId:", rid)
    print("[link] ", build_mp_link_from_review_id(rid, mp_id))
    print("[判重] 该 reviewId 已入库:", wx._is_article_gathered(mp_id, rid))

    # 2) 完整 get_Articles（首次：期望采集入库）
    print("\n=== 首次运行 ===")
    wx2 = MpsWereadMP()
    try:
        wx2.get_Articles(
            faker_id=mp_id, Mps_id=mp_id, Mps_title=mp_name,
            CallBack=callback, MaxPage=1, Gather_Content=True,
        )
        print(f"完成，本会话新增文章数: {len(wx2.articles)}")
    except WereadMPAPIError as exc:
        print(f"采集异常: code={exc.code} msg={exc.message} retriable={exc.retriable}")

    # 3) 二次运行：验证增量跳过（应无新文章）
    print("\n=== 二次运行（验证增量） ===")
    wx3 = MpsWereadMP()
    try:
        wx3.get_Articles(
            faker_id=mp_id, Mps_id=mp_id, Mps_title=mp_name,
            CallBack=callback, MaxPage=1, Gather_Content=True,
        )
        print(f"完成，本会话新增文章数: {len(wx3.articles)}")
    except WereadMPAPIError as exc:
        print(f"采集异常: code={exc.code} msg={exc.message} retriable={exc.retriable}")


if __name__ == "__main__":
    main()
