# -*- coding: utf-8 -*-
"""探测微信读书前端 JS 中 添加书架/关注/订阅 相关 API 路径"""
import io
import re
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0")
BASE = "https://weread.qq.com"

s = requests.Session()
s.headers.update({"User-Agent": UA})
html = s.get(f"{BASE}/", timeout=30).text

srcs = set()
for pat in (r'<script[^>]+src=["\']([^"\']+\.js)',
            r'<script[^>]+src=["\']([^"\']+)["\']'):
    for m in re.finditer(pat, html):
        c = m.group(1)
        if c.endswith(".js") or "web" in c:
            srcs.add(c)

out = io.StringIO()
out.write(f"js entries: {len(srcs)}\n")

seen = set()
queue = [(x, 0) for x in srcs]
paths = set()
total = 0
while queue and total < 400:
    src, dep = queue.pop(0)
    if src in seen:
        continue
    seen.add(src)
    url = src if src.startswith("http") else f"{BASE}/{src.lstrip('/')}"
    try:
        rr = s.get(url, timeout=25)
        if rr.status_code != 200:
            continue
        t = rr.text
    except Exception:
        continue
    total += 1
    for kw in ("shelf", "follow", "subscribe", "mp/add", "book/add", "operate", "collect"):
        for m in re.finditer(r'["\'](/[a-zA-Z0-9_\-/]*%s[a-zA-Z0-9_\-/]*)["\']' % re.escape(kw), t):
            paths.add((kw, m.group(1)))
    for m in re.finditer(r'wrFetchClient\(\s*["\'](/[^"\']+)["\']', t):
        p = m.group(1)
        if any(k in p for k in ("shelf", "follow", "add", "operate", "subscribe", "mp")):
            paths.add(("wrFetchClient", p))
    if dep < 3:
        for m in re.finditer(r'["\']([^"\']*\.js(?:\?[^"\']*)?)["\']', t):
            c = m.group(1)
            if c and "http" not in c and "//" not in c and c.endswith(".js"):
                queue.append((url.rsplit("/", 1)[0] + "/" + c, dep + 1))

out.write("=== shelf/follow/subscribe/add 相关路径 ===\n")
for tag, p in sorted(paths):
    out.write(f"[{tag}] {p}\n")

res = out.getvalue()
open("scripts/probe_shelf_add_api.txt", "w", encoding="utf-8").write(res)
print(res[:5000])
