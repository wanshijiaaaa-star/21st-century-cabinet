# -*- coding: utf-8 -*-
"""一次性修复：把已入库公众号文章 url 中被误替换的 ``~`` 恢复。

背景：旧版 ``build_mp_url`` 把 token 中的 ``~`` 替换成了 ``_``，
而微信服务器对 ``_`` 版本会 302 重定向回 ``~`` 版本，导致部分
阅读器无法正常打开。本脚本逐条请求验证，仅修正确实需要跳转的记录。

用法：python scripts/fix_weread_mp_urls.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

import requests

from core.db import DB
from core.models.article import Article

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36 "
    "MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI"
}
PREFIX = "https://mp.weixin.qq.com/s/"


def main():
    session = DB.get_session()
    try:
        rows = (
            session.query(Article)
            .filter(Article.mp_id.like("MP_WXS_%"), Article.url != "")
            .all()
        )
    finally:
        pass

    fixed, checked = 0, 0
    for art in rows:
        url = (art.url or "").strip()
        if not url.startswith(PREFIX):
            continue
        token = url[len(PREFIX):]
        if "~" in token:
            # 已是规范形式，无需处理
            continue
        checked += 1
        try:
            resp = requests.get(url, headers=UA, timeout=15, allow_redirects=False)
        except requests.RequestException as exc:
            print(f"[跳过] {art.id} {url} 请求失败: {exc}")
            continue
        location = resp.headers.get("Location", "")
        if resp.status_code == 302 and location.startswith(PREFIX):
            # 只处理 token 层面的纠错：_ -> ~（微信 302 回规范链接）。
            # 忽略 ?nwr_flag=1 这类微信风控跳转参数（跟随重定向后仍可访问）。
            new_token = location[len(PREFIX):].split("?")[0]
            if new_token != token and "~" in new_token:
                fixed_url = f"{PREFIX}{new_token}"
                print(f"[修复] {art.id}\n  {url}\n  -> {fixed_url}")
                art.url = fixed_url
                session.add(art)
                fixed += 1
            else:
                print(f"[无需] {art.id} {url}（302 仅风控跳转 {location}）")
        else:
            print(f"[正常] {art.id} {url}（HTTP {resp.status_code}）")
        time.sleep(0.5)

    if fixed:
        session.commit()
    session.close()
    print(f"\n共检查 {checked} 条，修复 {fixed} 条")


if __name__ == "__main__":
    main()
