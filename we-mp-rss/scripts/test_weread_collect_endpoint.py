# -*- coding: utf-8 -*-
"""实测 collect 端点：模拟前端 WereadManagement 书架采集公众号文章。

验证：WEREAD_ 前缀规范化、自动创建 feeds 订阅源、cover 采集入库、
update_mps 不再报"未找到"。
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

from apis.weread import WereadCollectRequest, collect_weread_notes
from core.db import DB
from core.models.feed import Feed


async def main():
    # 与前端 WereadManagement.collectBookNotes 完全一致的传参
    req = WereadCollectRequest(
        mp_id="WEREAD_MP_WXS_3012726261",
        mp_name="长沙开福区",
        faker_id="MP_WXS_3012726261",
    )
    resp = await collect_weread_notes(req, current_user=None)
    print("\n[collect 响应]")
    if isinstance(resp, dict):
        body = resp.get("body") or resp
        print(f"  code={body.get('code')} msg={body.get('message')}")
        data = body.get("data") or {}
        print(f"  collected={data.get('collected')}")
        for art in (data.get("articles") or [])[:3]:
            print(f"  - {art.get('title')} | {art.get('url')} | mp_id={art.get('mp_id')}")
    else:
        print("  ", resp)

    s = DB.get_session()
    try:
        feed = s.query(Feed).filter(Feed.id == "MP_WXS_3012726261").first()
        print("\n[feeds 表] MP_WXS_3012726261:", 
              f"存在 | mp_name={feed.mp_name} | faker_id={feed.faker_id}" if feed else "不存在")
    finally:
        s.close()


if __name__ == "__main__":
    asyncio.run(main())
