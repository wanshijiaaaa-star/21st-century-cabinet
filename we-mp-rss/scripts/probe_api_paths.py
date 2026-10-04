# -*- coding: utf-8 -*-
"""抓取前端 JS 全部 wrFetchClient 调用的 API 路径 + 含 mp/article 关键词的调用"""
import re
import sys
from urllib.parse import urljoin

import requests

sys.stdout.reconfigure(encoding="utf-8")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0")
BASE = "https://weread.qq.com"

s = requests.Session()
s.headers.update({"User-Agent": UA})
html = s.get(f"{BASE}/", timeout=30).text

srcs = set()
for pat in (r'<script[^>]+src=["\']([^"\']+)["\']',
            r'<link[^>]+rel="modulepreload"[^>]+href=["\']([^"\']+)["\']'):
    for m in re.finditer(pat, html):
        srcs.add(m.group(1))
srcs = [x for x in srcs if x.endswith(".js") and not x.startswith("data:")]

seen = set()
queue = [(x, 0) for x in srcs]
api_calls = set()
mp_snippets = []
total = 0
while queue and total < 500:
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
    # wrFetchClient 调用路径
    for m in re.finditer(r'wrFetchClient\(\s*["\'](/[^"\']+)["\']', text):
        api_calls.add(m.group(1))
    for m in re.finditer(r'["\'](/web/[a-zA-Z0-9_\-/]+)["\']', text):
        p = m.group(1)
        if any(k in p for k in ("mp", "article", "feed", "bookmark", "review", "note")):
            api_calls.add(p)
    for m in re.finditer(r'["\'](/api/[a-zA-Z0-9_\-/]+)["\']', text):
        p = m.group(1)
        if any(k in p for k in ("mp", "article", "feed", "bookmark", "review", "note", "shelf")):
            api_calls.add(p)
    # mp 相关上下文
    for m in re.finditer(r'mp[a-zA-Z]*', text, re.I):
        start = max(0, m.start() - 80)
        end = min(len(text), m.end() + 120)
        snip = re.sub(r"\s+", " ", text[start:end])
        if any(k in snip for k in ("articles", "article", "feed", "list", "reader", "content")):
            mp_snippets.append((src[-45:], snip))

out = []
out.append("=== 全部 API 调用路径（mp/article 相关） ===")
for p in sorted(api_calls):
    out.append(f"  {p}")
out.append(f"\n=== mp 相关代码片段（{len(mp_snippets)} 处，前 40） ===")
for src, snip in mp_snippets[:40]:
    out.append(f"  [{src}]\n    ...{snip}...")

res = "\n".join(out)
open("scripts/probe_result.txt", "w", encoding="utf-8").write(res)
print(res)
