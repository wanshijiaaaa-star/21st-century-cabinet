# -*- coding: utf-8 -*-
"""实测 POST /web/shelf/add 不同请求体格式的响应，确认字段名。"""
import io
import json
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
H = {
    "User-Agent": UA,
    "Content-Type": "application/json",
    "Origin": "https://weread.qq.com",
    "Referer": "https://weread.qq.com/",
    "Cookie": "wr_vid=0; wr_skey=invalid_cookie_probe",
}
out = io.StringIO()
bodies = [
    {"bookId": "MP_WXS_3528995129"},
    {"bookIds": ["MP_WXS_3528995129"]},
    {"bookIds": "MP_WXS_3528995129"},
    {"bookInfo": {"bookId": "MP_WXS_3528995129"}},
    {"bids": ["MP_WXS_3528995129"]},
    {},
]
for b in bodies:
    try:
        r = requests.post("https://weread.qq.com/web/shelf/add", json=b, headers=H, timeout=15)
        out.write(f"{json.dumps(b, ensure_ascii=False):<60} -> HTTP {r.status_code} {r.text[:120]}\n")
    except Exception as e:
        out.write(f"{json.dumps(b, ensure_ascii=False):<60} -> ERR {e}\n")

# 顺带实测 web/shelf/sync 空 userVid 对照
try:
    r = requests.get("https://weread.qq.com/web/shelf/sync",
                     params={"userVid": "", "synckey": 0, "lectureSynckey": 0},
                     headers=H, timeout=15)
    out.write(f"{'shelf/sync 对照':<60} -> HTTP {r.status_code} {r.text[:120]}\n")
except Exception as e:
    out.write(f"{'shelf/sync 对照':<60} -> ERR {e}\n")

res = out.getvalue()
open("scripts/probe_shelf_add_body.txt", "w", encoding="utf-8").write(res)
print(res)
