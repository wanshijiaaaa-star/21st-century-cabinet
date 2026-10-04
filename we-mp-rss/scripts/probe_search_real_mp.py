# -*- coding: utf-8 -*-
"""用真实公众号名称搜索，确认 search/global 返回的 bookId 形态与字段。"""
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
for kw in ("麦乐在长沙", "央视新闻", "长沙发布"):
    try:
        r = requests.get("https://weread.qq.com/web/search/global",
                         params={"keyword": kw, "maxIdx": 0, "count": 20},
                         headers=H, timeout=20)
        out.write(f"=== keyword={kw} HTTP {r.status_code} ===\n")
        try:
            data = r.json()
        except Exception:
            out.write(r.text[:400] + "\n")
            continue
        books = data.get("books") or []
        out.write(f"books count={len(books)}\n")
        for item in books[:10]:
            bi = item.get("bookInfo") or {}
            bid = bi.get("bookId", "")
            title = bi.get("title") or bi.get("name") or ""
            author = bi.get("author") or ""
            btype = bi.get("bookType") or ""
            out.write(f"   bookId={bid} | bookType={btype} | title={title} | author={author} | subscribeCount={item.get('subscribeCount')}\n")
            if bid.startswith("MP_WXS") or kw in title:
                out.write(f"   FULL item keys: {list(item.keys())}\n")
                out.write(f"   bookInfo keys: {list(bi.keys())}\n")
        out.write("\n")
    except Exception as e:
        out.write(f"ERR {e}\n")

res = out.getvalue()
open("scripts/probe_search_real_mp.txt", "w", encoding="utf-8").write(res)
print(res)
