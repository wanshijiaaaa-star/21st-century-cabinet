# -*- coding: utf-8 -*-
"""实测书架 4 本书的 bookmarklist，确认 0 条笔记是接口问题还是书无划线"""
import json
import requests

raw = open("data/wx.lic", encoding="utf-8").read()
cookie = ""
for line in raw.splitlines():
    if "cookie:" in line and "wr_" in line:
        cookie = line.split("cookie:", 1)[1].strip().strip("'").strip()
        break

headers = {
    "Cookie": cookie,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Origin": "https://weread.qq.com",
    "Referer": "https://weread.qq.com/",
}

# 1) 书架
r = requests.get("https://weread.qq.com/web/shelf/sync",
                 params={"userVid": "", "synckey": 0, "lectureSynckey": 0},
                 headers=headers, timeout=20)
j = r.json()
books = j.get("books", [])
out = [f"shelf: HTTP {r.status_code} bookCount={j.get('bookCount')}"]
for b in books:
    out.append(f"  bookId={b.get('bookId')} title={b.get('title')!r} format={b.get('format')}")

# 2) 每本书 bookmarklist + bookmarkList + 带 listType
for b in books:
    bid = b.get("bookId")
    for path, params in (
        ("/web/book/bookmarklist", {"bookId": bid}),
        ("/web/book/bookmarklist", {"bookId": bid, "listType": 0}),
        ("/web/book/bookmarklist", {"bookId": bid, "synckey": 0}),
    ):
        try:
            r2 = requests.get("https://weread.qq.com" + path, params=params,
                              headers=headers, timeout=20)
            body = r2.text[:120].replace("\n", " ")
            out.append(f"  [{bid[:30]}...] {path} {params} -> HTTP {r2.status_code} {body!r}")
        except Exception as e:
            out.append(f"  [{bid[:30]}...] {path} ERR {e}")

print("\n".join(out))
open("scripts/probe_result.txt", "w", encoding="utf-8").write("\n".join(out))
