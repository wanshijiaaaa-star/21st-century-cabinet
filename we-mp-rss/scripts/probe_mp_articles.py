# -*- coding: utf-8 -*-
"""探测 /web/mp/articles 的 -2041 触发条件（cookie / ticket / 参数）"""
import requests

raw = open("data/wx.lic", encoding="utf-8").read()
cookie = ""
for line in raw.splitlines():
    if "cookie:" in line and "wr_" in line:
        cookie = line.split("cookie:", 1)[1].strip().strip("'").strip()
        break

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0")

BOOK = "MP_WXS_3556030239"

def try_get(tag, headers, params):
    try:
        r = requests.get("https://weread.qq.com/web/mp/articles",
                         params=params, headers=headers, timeout=20)
        return f"[{tag}] HTTP {r.status_code} {r.text[:150]!r}"
    except Exception as e:
        return f"[{tag}] ERR {e}"

cases = [
    ("no-cookie", {"User-Agent": UA}, {"bookId": BOOK, "offset": 0}),
    ("cookie", {
        "Cookie": cookie, "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Origin": "https://weread.qq.com", "Referer": "https://weread.qq.com/",
    }, {"bookId": BOOK, "offset": 0}),
    ("cookie+count", {
        "Cookie": cookie, "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Origin": "https://weread.qq.com", "Referer": "https://weread.qq.com/",
    }, {"bookId": BOOK, "offset": 0, "count": 20}),
    ("cookie+faketicket", {
        "Cookie": cookie, "User-Agent": UA,
        "x-wr-ticket": "fake-ticket-123",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://weread.qq.com", "Referer": "https://weread.qq.com/",
    }, {"bookId": BOOK, "offset": 0}),
    ("cookie+listType11", {
        "Cookie": cookie, "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://weread.qq.com", "Referer": "https://weread.qq.com/",
    }, {"bookId": BOOK, "offset": 0, "listType": 11}),
]

out = [try_get(*c) for c in cases]
print("\n".join(out))
open("scripts/probe_result.txt", "w", encoding="utf-8").write("\n".join(out))
