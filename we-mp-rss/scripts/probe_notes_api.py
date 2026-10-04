# -*- coding: utf-8 -*-
"""实测长沙人社(MP_WXS_3556030239)的笔记/划线候选接口，定位 0 条笔记原因"""
import requests

raw = open("data/wx.lic", encoding="utf-8").read()
cookie = ""
for line in raw.splitlines():
    if "cookie:" in line and "wr_" in line:
        cookie = line.split("cookie:", 1)[1].strip().strip("'").strip()
        break
print("COOKIE =", cookie)
print()

BOOK_ID = "MP_WXS_3556030239"
headers = {
    "Cookie": cookie,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Origin": "https://weread.qq.com",
    "Referer": "https://weread.qq.com/",
}

cases = [
    # web 域
    ("web /web/book/bookmarklist", "https://weread.qq.com/web/book/bookmarklist",
     {"bookId": BOOK_ID}),
    ("web /web/book/bookmarkList", "https://weread.qq.com/web/book/bookmarkList",
     {"bookId": BOOK_ID}),
    ("web /web/book/bookmarklist synckey", "https://weread.qq.com/web/book/bookmarklist",
     {"bookId": BOOK_ID, "synckey": 0, "listType": 0}),
    ("web /web/mp/articles", "https://weread.qq.com/web/mp/articles",
     {"bookId": BOOK_ID, "offset": 0}),
    ("web /web/mp/notes", "https://weread.qq.com/web/mp/notes",
     {"bookId": BOOK_ID, "offset": 0}),
    ("web /web/mp/bookmarklist", "https://weread.qq.com/web/mp/bookmarklist",
     {"bookId": BOOK_ID}),
    ("web /web/mp/noteList", "https://weread.qq.com/web/mp/noteList",
     {"bookId": BOOK_ID}),
    # mp 域
    ("mp  mp.weread.qq.com/web/book/bookmarklist", "https://mp.weread.qq.com/web/book/bookmarklist",
     {"bookId": BOOK_ID}),
    ("mp  mp.weread.qq.com/web/mp/articles", "https://mp.weread.qq.com/web/mp/articles",
     {"bookId": BOOK_ID, "offset": 0}),
    # i 域对照
    ("i   i.weread.qq.com/book/bookmarklist", "https://i.weread.qq.com/book/bookmarklist",
     {"bookId": BOOK_ID}),
]

out = []
for tag, url, params in cases:
    try:
        r = requests.get(url, params=params, headers=headers, timeout=20)
        body = r.text[:200].replace("\n", " ")
        out.append(f"[{tag}]\n  HTTP {r.status_code}  body: {body!r}")
    except Exception as e:
        out.append(f"[{tag}]\n  ERR {e}")

print("\n\n".join(out))
open("scripts/probe_result.txt", "w", encoding="utf-8").write("\n\n".join(out))
