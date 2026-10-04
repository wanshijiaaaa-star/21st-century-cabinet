# -*- coding: utf-8 -*-
"""跑 mp/articles 变体矩阵（V1-V20）定位 -2041（复制自 weread_scan_diag._probe_mp_variants）"""
import re
from urllib.parse import urljoin, quote

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0")
BASE = "https://weread.qq.com"

raw = open("data/wx.lic", encoding="utf-8").read()
cookies = {}
for line in raw.splitlines():
    if "cookie:" in line and "wr_" in line:
        c = line.split("cookie:", 1)[1].strip().strip("'").strip()
        for part in c.split(";"):
            k, _, v = part.strip().partition("=")
            if k:
                cookies[k] = v

VID = cookies.get("wr_vid", "")
BOOK = "MP_WXS_3556030239"

chrome148 = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
             "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
minimal = {"User-Agent": chrome148, "Accept": "application/json, text/plain, */*"}
full = {"User-Agent": UA, "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9", "Origin": "https://weread.qq.com",
        "Referer": "https://weread.qq.com/"}
base = {"bookId": BOOK, "offset": 0}
cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())

cases = []

def add(label, method, headers, params, data=None, json_body=None):
    cases.append((label, method, headers, params, data, json_body))

add("V1 base", "GET", full, base)
add("V2 +count=20", "GET", full, {**base, "count": 20})
add("V3 +count=10", "GET", full, {**base, "count": 10})
add("V4 +listType=2", "GET", full, {**base, "listType": 2})
add("V5 +listType=1", "GET", full, {**base, "listType": 1})
add("V6 +count20+listType2", "GET", full, {**base, "count": 20, "listType": 2})
add("V7 no-offset", "GET", full, {"bookId": BOOK})
add("V8 +uid=<vid>", "GET", full, {**base, "uid": VID})
add("V9 POST form", "POST", full, {}, data={"bookId": BOOK, "offset": 0})
add("V10 POST json", "POST", full, {}, json_body={"bookId": BOOK, "offset": 0})
add("V11 最小头 Chrome148", "GET", minimal, base)
add("V12 完整头 Chrome148", "GET", {**full, "User-Agent": chrome148}, base)
add("V13 纯数字bookId", "GET", full, {"bookId": str(BOOK).replace("MP_WXS_", ""), "offset": 0})
add("V14 带x-wr-ticket空", "GET", {**full, "x-wr-ticket": ""}, base)
add("V15 无Origin/Referer", "GET", {k: v for k, v in full.items() if k not in ("Origin", "Referer")}, base)
add("V16 无Cookie", "GET", full, base)
add("V17 +synckey=0", "GET", full, {**base, "synckey": 0})
add("V18 +listType2+count20+synckey", "GET", full, {**base, "count": 20, "listType": 2, "synckey": 0})
add("V19 ticket=wr_skey", "GET", {**full, "x-wr-ticket": cookies.get("wr_skey", "")}, base)
add("V20 +subType=1", "GET", full, {**base, "subType": 1})
add("V21 +limit=20", "GET", full, {**base, "limit": 20})
add("V22 +page=1", "GET", full, {**base, "page": 1})
add("V23 +orderType=1", "GET", full, {**base, "orderType": 1})
add("V24 +sort=2", "GET", full, {**base, "sort": 2})

out = []
for label, method, headers, params, data, json_body in cases:
    h = dict(headers)
    if label != "V16 无Cookie":
        h["Cookie"] = cookie_str
    try:
        if method == "POST":
            r = requests.post(f"{BASE}/web/mp/articles", params=params, data=data,
                              json=json_body, headers=h, timeout=20)
        else:
            r = requests.get(f"{BASE}/web/mp/articles", params=params, headers=h, timeout=20)
        try:
            j = r.json()
            code = j.get("errCode", j.get("errcode", 0))
            n = len(j.get("reviews") or [])
        except Exception:
            code = f"non-json HTTP {r.status_code}"
            n = 0
        mark = " >>> OK" if code == 0 else ""
        out.append(f"  {label:<22} {method:<4} code={code} reviews={n}{mark}")
    except Exception as e:
        out.append(f"  {label:<22} {method:<4} err {e}")

# 全部订阅号逐一验证
out.append("\n--- 全部订阅号逐一验证 base GET ---")
try:
    h = dict(full)
    h["Cookie"] = cookie_str
    r = requests.get(f"{BASE}/web/shelf/sync", params={"userVid": "", "synckey": 0},
                     headers=h, timeout=20)
    j = r.json()
    for b in (j.get("books") or []):
        bid = b.get("bookId")
        if not bid or not str(bid).startswith("MP_WXS_"):
            continue
        h2 = dict(full)
        h2["Cookie"] = cookie_str
        r2 = requests.get(f"{BASE}/web/mp/articles", params={"bookId": bid, "offset": 0},
                          headers=h2, timeout=20)
        j2 = r2.json()
        code = j2.get("errCode", j2.get("errcode", 0))
        n = len(j2.get("reviews") or [])
        mark = " >>> OK" if code == 0 else ""
        out.append(f"  {bid:<26} code={code} reviews={n}{mark}")
except Exception as e:
    out.append(f"  shelf err {e}")

# 替代路径
out.append("\n--- 其它可能路径探测 ---")
for alt in ("/mp/articles", "/wr/mp/articles", "/web/mp/feeds", "/web/feed/mp",
            "/web/mp/articles/page", "/web/mp/articleList", "/web/mp/list"):
    h = dict(full)
    h["Cookie"] = cookie_str
    try:
        r = requests.get(f"{BASE}{alt}", params=base, headers=h, timeout=20)
        try:
            j = r.json()
            code = j.get("errCode", j.get("errcode", 0))
            body = str(j)[:100]
        except Exception:
            code = "non-json"
            body = r.text[:100]
        mark = " >>> OK" if code == 0 else ""
        out.append(f"  {alt:<26} code={code}{mark} body={body!r}")
    except Exception as e:
        out.append(f"  {alt:<26} err {e}")

import sys
sys.stdout.reconfigure(encoding="utf-8")
res = "\n".join(out)
open("scripts/probe_result.txt", "w", encoding="utf-8").write(res)
print(res)
