# -*- coding: utf-8 -*-
"""深度搜索微信读书前端 JS：构造「加入书架」请求的代码片段。"""
import io
import re
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0")
BASE = "https://weread.qq.com"

s = requests.Session()
s.headers.update({"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
html = s.get(f"{BASE}/", timeout=30).text

srcs = set()
for pat in (r'<script[^>]+src=["\']([^"\']+)["\']',
            r'import\s*\(["\']([^"\']+)["\']\)'):
    for m in re.finditer(pat, html):
        c = m.group(1)
        if c.endswith(".js") or "web" in c or "asset" in c:
            srcs.add(c)

seen = set()
queue = [(x, 0) for x in srcs]
hits = []
total = 0
while queue and total < 900:
    src, dep = queue.pop(0)
    if src in seen:
        continue
    seen.add(src)
    url = src if src.startswith("http") else f"{BASE}/{src.lstrip('/')}"
    try:
        rr = s.get(url, timeout=20)
        if rr.status_code != 200:
            continue
        t = rr.text
    except Exception:
        continue
    total += 1
    # 关键词：bookIds / addShelf / shelfAdd / 拼接式 /web/shelf
    for key in ("bookIds", "bookId", "addShelf", "shelfAdd", "addToShelf", "shelf/add"):
        idx = 0
        while True:
            i = t.find(key, idx)
            if i < 0:
                break
            ctx = t[max(0, i - 260): i + 320].replace("\n", " ")
            hits.append((key, src, ctx))
            idx = i + 1
            if len(hits) > 120:
                break
        if len(hits) > 120:
            break
    if dep < 3:
        for m in re.finditer(r'["\']([^"\']*\.js(?:\?[^"\']*)?)["\']', t):
            c = m.group(1)
            if c and "http" not in c and "//" not in c and c.endswith(".js"):
                queue.append((url.rsplit("/", 1)[0] + "/" + c, dep + 1))
    if len(hits) > 120:
        break

out = io.StringIO()
out.write(f"total js fetched: {total}\n\n")
for key, src, ctx in hits[:120]:
    out.write(f"--- [{key}] in {src}\n{ctx}\n\n")
res = out.getvalue()
open("scripts/probe_shelf_add_deep.txt", "w", encoding="utf-8").write(res)
print(f"total js fetched: {total}, hits: {len(hits)}")
print(res[:8000])
