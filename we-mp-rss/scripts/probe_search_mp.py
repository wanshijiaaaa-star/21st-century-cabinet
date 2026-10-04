# -*- coding: utf-8 -*-
"""实测 GET /web/search/global 搜索公众号，确认返回结构中 MP_WXS_ 形态。"""
import io
import json
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
H = {
    "User-Agent": UA,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://weread.qq.com/web/search/global?keyword=xx",
}
out = io.StringIO()
for kw in ("微信读书", "36氪"):
    try:
        r = requests.get("https://weread.qq.com/web/search/global",
                         params={"keyword": kw, "maxIdx": 0, "count": 20},
                         headers=H, timeout=20)
        out.write(f"=== keyword={kw} HTTP {r.status_code} ===\n")
        try:
            data = r.json()
        except Exception:
            out.write(r.text[:500] + "\n")
            continue
        out.write(f"top keys: {list(data.keys())}\n")
        for section in ("books", "mp", "web"):
            items = data.get(section) or data.get("books") or []
            if not isinstance(items, list):
                continue
            out.write(f"[{section}] count={len(items)}\n")
            for item in items[:8]:
                bi = item.get("bookInfo") or item
                bid = bi.get("bookId", "")
                name = bi.get("title") or bi.get("name") or ""
                author = bi.get("author") or ""
                out.write(f"   bookId={bid} | title={name} | author={author} | keys={list(item.keys())[:12]}\n")
            break
        out.write("\n")
    except Exception as e:
        out.write(f"ERR {e}\n")

res = out.getvalue()
open("scripts/probe_search_mp.txt", "w", encoding="utf-8").write(res)
print(res)
