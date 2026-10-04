# -*- coding: utf-8 -*-
"""探测微信读书 web 域 添加书架/关注 候选接口是否存在。

策略：用无效 Cookie 请求，若路径不存在返回 404/405，存在则返回 200+业务码(-2012 等) 或 401/403。
"""
import io
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0")
HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Origin": "https://weread.qq.com",
    "Referer": "https://weread.qq.com/",
    "Cookie": "wr_vid=0; wr_skey=invalid_cookie_probe",
}
BASE = "https://weread.qq.com"

cases = [
    # (label, method, path, params, data)
    ("shelf/add GET",   "GET",  "/web/shelf/add", {"bookId": "MP_WXS_3528995129"}, None),
    ("shelf/add POST",  "POST", "/web/shelf/add", None, {"bookId": "MP_WXS_3528995129"}),
    ("shelf/operate",   "GET",  "/web/shelf/operate", {"bookId": "MP_WXS_3528995129", "op": 1}, None),
    ("book/operate",    "GET",  "/web/book/operate", {"bookId": "MP_WXS_3528995129", "op": 1}, None),
    ("book/add",        "GET",  "/web/book/add", {"bookId": "MP_WXS_3528995129"}, None),
    ("ebook/add",       "GET",  "/web/ebook/add", {"bookId": "MP_WXS_3528995129"}, None),
    ("mp/follow",       "GET",  "/web/mp/follow", {"bookId": "MP_WXS_3528995129"}, None),
    ("mp/subscribe",    "GET",  "/web/mp/subscribe", {"bookId": "MP_WXS_3528995129"}, None),
    ("feed/follow",     "GET",  "/web/feed/follow", {"bookId": "MP_WXS_3528995129"}, None),
    ("search/global",   "GET",  "/web/search/global", {"keyword": "测试", "maxIdx": 0, "count": 20}, None),
    ("search/books",    "GET",  "/web/search/books", {"keyword": "测试", "maxIdx": 0, "count": 20}, None),
    ("shelf/sync(ref)", "GET",  "/web/shelf/sync", {"userVid": "", "synckey": 0}, None),
]

out = io.StringIO()
for label, method, path, params, data in cases:
    url = BASE + path
    try:
        if method == "GET":
            r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        else:
            r = requests.post(url, params=params, json=data, headers=HEADERS, timeout=15)
        body = r.text[:120].replace("\n", " ")
        out.write(f"{label:<22} -> HTTP {r.status_code} len={len(r.content)} body={body!r}\n")
    except Exception as e:
        out.write(f"{label:<22} -> ERR {e}\n")

res = out.getvalue()
open("scripts/probe_shelf_add_endpoint.txt", "w", encoding="utf-8").write(res)
print(res)
