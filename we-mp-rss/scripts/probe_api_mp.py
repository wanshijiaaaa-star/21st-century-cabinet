# -*- coding: utf-8 -*-
"""实测 /api/mp/* 系列接口（新版前端真实接口）+ 找 wrFetchClient baseURL"""
import re
import sys
from urllib.parse import urljoin

import requests

sys.stdout.reconfigure(encoding="utf-8")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0")
BASE = "https://weread.qq.com"

raw = open("data/wx.lic", encoding="utf-8").read()
cookie = ""
for line in raw.splitlines():
    if "cookie:" in line and "wr_" in line:
        cookie = line.split("cookie:", 1)[1].strip().strip("'").strip()
        break

FULL = {"User-Agent": UA, "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9", "Origin": "https://weread.qq.com",
        "Referer": "https://weread.qq.com/", "Cookie": cookie}

BOOK = "MP_WXS_3556030239"
out = []

# 1) /api/mp/* 穷举
paths = [
    "/api/mp/cover", "/api/mp/articles", "/api/mp/articleList", "/api/mp/list",
    "/api/mp/notes", "/api/mp/noteList", "/api/mp/bookmarklist",
    "/api/mp/readerInfo", "/api/mp/mpInfo", "/api/mp/reviews",
    "/api/mp/article", "/api/mp/latest", "/api/mp/feed",
]
for p in paths:
    try:
        r = requests.get(BASE + p, params={"bookId": BOOK, "offset": 0},
                         headers=FULL, timeout=15)
        body = r.text[:150].replace("\n", " ")
        out.append(f"[{p}] HTTP {r.status_code} {body!r}")
    except Exception as e:
        out.append(f"[{p}] ERR {e}")

# 2) 抓 wrFetchClient 定义（baseURL 前缀）
s = requests.Session()
s.headers.update({"User-Agent": UA})
try:
    r = s.get(f"{BASE}/", timeout=30)
    html = r.text
    srcs = set()
    for pat in (r'<script[^>]+src=["\']([^"\']+)["\']',
                r'<link[^>]+rel="modulepreload"[^>]+href=["\']([^"\']+)["\']'):
        for m in re.finditer(pat, html):
            srcs.add(m.group(1))
    srcs = [x for x in srcs if x.endswith(".js") and not x.startswith("data:")]
    seen = set()
    queue = [(x, 0) for x in srcs]
    found = []
    total = 0
    while queue and total < 300:
        src, dep = queue.pop(0)
        if src in seen:
            continue
        seen.add(src)
        url = urljoin(f"{BASE}/", src)
        try:
            rr = s.get(url, timeout=25)
            if rr.status_code != 200:
                continue
            text = rr.text
        except Exception:
            continue
        total += 1
        if dep < 3:
            for m in re.finditer(r'["\']([^"\']*\.js(?:\?[^"\']*)?)["\']', text):
                c = m.group(1)
                if c and not c.startswith("http") and "//" not in c:
                    queue.append((urljoin(url, c), dep + 1))
        idx = text.find("wrFetchClient")
        if idx >= 0:
            start = max(0, idx - 300)
            end = min(len(text), idx + 600)
            snippet = re.sub(r"\s+", " ", text[start:end])
            found.append(f"[{src[-50:]}]\n    {snippet}")
    out.append(f"\n--- wrFetchClient 定义（抓 {total} 个 JS） ---")
    out.extend(found[:6] if found else ["(未找到 wrFetchClient 定义)"])
except Exception as e:
    out.append(f"wrFetchClient 抓取失败: {e}")

res = "\n".join(out)
open("scripts/probe_result.txt", "w", encoding="utf-8").write(res)
print(res)
