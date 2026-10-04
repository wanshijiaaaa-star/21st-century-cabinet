# -*- coding: utf-8 -*-
"""深度抓取前端 JS，找公众号文章列表真实接口（新版前端已不用 /web/mp/articles）"""
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

s = requests.Session()
s.headers.update({"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
if cookie:
    s.headers["Cookie"] = cookie

out = []
try:
    r = s.get(f"{BASE}/", timeout=30)
    html = r.text
except Exception as e:
    out.append(f"首页失败: {e}")
    html = ""

# 收集全部 JS 入口
srcs = set()
for pat in (r'<script[^>]+src=["\']([^"\']+)["\']',
            r'<link[^>]+rel="modulepreload"[^>]+href=["\']([^"\']+)["\']',
            r'<link[^>]+rel="preload"[^>]+as="script"[^>]+href=["\']([^"\']+)["\']'):
    for m in re.finditer(pat, html):
        srcs.add(m.group(1))
srcs = [x for x in srcs if x.endswith(".js") and not x.startswith("data:")]

# 关键词（公众号文章相关）
keywords = ["/api/mp/", "mp/reader", "articleList", "mpList", "getArticles",
            "getMpArticle", "articles", "reviewList", "subReviews", "mpArticle",
            "MP_ARTICLE", "BOOK_TYPE_MP", "mpDetail", "mpInfo", "reviewId"]
hits = {}
seen = set()
queue = [(src, 0, src) for src in srcs]
total = 0
while queue and total < 1200:
    src, dep, ref = queue.pop(0)
    if src in seen:
        continue
    seen.add(src)
    url = urljoin(f"{BASE}/", src)
    try:
        rr = s.get(url, timeout=25)
        if rr.status_code != 200 or len(rr.content) > 10_000_000:
            continue
        text = rr.text
    except Exception:
        continue
    total += 1
    if dep < 6:
        for m in re.finditer(r'["\']([^"\']*\.js(?:\?[^"\']*)?)["\']', text):
            c = m.group(1)
            if not c or c.startswith("http") or "//" in c:
                continue
            full = urljoin(url, c)
            if full not in seen:
                queue.append((full, dep + 1, src[:60]))
    for kw in keywords:
        if kw not in text:
            continue
        for m in re.finditer(re.escape(kw), text):
            start = max(0, m.start() - 150)
            end = min(len(text), m.end() + 250)
            snippet = re.sub(r"\s+", " ", text[start:end])
            key = (kw, snippet[:60])
            hits.setdefault(kw, [])
            if key not in hits[kw]:
                hits[kw].append((src[-40:], snippet))

out.append(f"已抓取 {total} 个 JS")
if not hits:
    out.append("(无命中)")
else:
    for kw, items in hits.items():
        out.append(f"\n--- 命中 {kw!r}（{len(items)} 处） ---")
        for src, snippet in items[:6]:
            out.append(f"  [{src}]\n    ...{snippet}...")

res = "\n".join(out)
open("scripts/probe_result.txt", "w", encoding="utf-8").write(res)
print(res)
