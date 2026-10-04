# -*- coding: utf-8 -*-
"""用当前 wx.lic 保存的 cookie 实测 web 域 / i 域各接口，定位 401 来源"""
import json
import requests

# 当前 wx.lic 保存的 cookie（明文 YAML 读取）
raw = open("data/wx.lic", encoding="utf-8").read()
cookie = ""
for line in raw.splitlines():
    if "weread_data:" in line:
        pass
    if "cookie:" in line and "wr_" in line:
        cookie = line.split("cookie:", 1)[1].strip().strip("'").strip()
        break
print("COOKIE =", cookie)
print()

VID = "263045044"
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
    ("web", "https://weread.qq.com/web/shelf/sync",
     {"userVid": "", "synckey": 0, "lectureSynckey": 0}),
    ("web", "https://weread.qq.com/web/book/bookmarklist",
     {"bookId": "MP_WXS_3528995129"}),
    ("web", "https://weread.qq.com/web/book/info",
     {"bookId": "MP_WXS_3528995129"}),
    ("web", "https://weread.qq.com/web/review/list",
     {"bookId": "MP_WXS_3528995129", "listType": 11}),
    ("web", "https://weread.qq.com/web/mp/articles",
     {"bookId": "MP_WXS_3528995129", "offset": 0}),
    ("i",   "https://i.weread.qq.com/shelf/sync",
     {"userVid": VID, "synckey": 0, "lectureSynckey": 0}),
]

out = []
for tag, url, params in cases:
    try:
        r = requests.get(url, params=params, headers=headers, timeout=20)
        body = r.text[:160].replace("\n", " ")
        out.append(f"[{tag}] HTTP {r.status_code} {url.replace('https://', '')}?{params}\n  body: {body!r}")
    except Exception as e:
        out.append(f"[{tag}] ERR {url}: {e}")

print("\n\n".join(out))
open("scripts/probe_result.txt", "w", encoding="utf-8").write("\n\n".join(out))
