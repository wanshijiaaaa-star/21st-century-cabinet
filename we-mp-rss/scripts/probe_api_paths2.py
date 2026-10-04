# -*- coding: utf-8 -*-
"""提取微信读书前端 JS 中所有 wrFetchClient/$fetch/api 调用路径，找 shelf/book/collect/follow 相关。"""
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
api_paths = set()
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
    for pat in (r'wrFetchClient\(\s*["\'](/[^"\']+)["\']',
                r'["\'](/api/[a-zA-Z0-9_\-/]+)["\']',
                r'["\'](/web/[a-zA-Z0-9_\-/]+)["\']'):
        for m in re.finditer(pat, t):
            api_paths.add(m.group(1))
    if dep < 3:
        for m in re.finditer(r'["\']([^"\']*\.js(?:\?[^"\']*)?)["\']', t):
            c = m.group(1)
            if c and "http" not in c and "//" not in c and c.endswith(".js"):
                queue.append((url.rsplit("/", 1)[0] + "/" + c, dep + 1))

out = io.StringIO()
out.write(f"total js fetched: {total}, unique paths: {len(api_paths)}\n\n")
for p in sorted(api_paths):
    flag = ""
    if any(k in p for k in ("shelf", "book", "collect", "follow", "add", "subscribe", "mp", "operate")):
        flag = "  <== 关注"
    out.write(f"{p}{flag}\n")
res = out.getvalue()
open("scripts/probe_api_paths2.txt", "w", encoding="utf-8").write(res)
print(res)
