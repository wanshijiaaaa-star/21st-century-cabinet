# -*- coding: utf-8 -*-
"""抓取 weread.qq.com 前端 JS（含懒加载 chunk），提取公众号文章真实接口与参数"""
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
    out.append(f"首页 HTML {len(html)}B status={r.status_code}")
except Exception as e:
    out.append(f"首页失败: {e}")
    html = ""

# 1) SSR 公众号路由
mp_links = sorted(set(re.findall(r'/web/[a-zA-Z0-9_\-/]*MP_WXS_\d+', html)))
out.append(f"[SSR公众号路由] {mp_links[:20]}")
if not mp_links:
    # 直接尝试公众号阅读页
    for cand in (f"/web/reader?bookId=MP_WXS_3556030239",
                 f"/book-detail?type=1&v=MP_WXS_3556030239",
                 f"/web/mp?bookId=MP_WXS_3556030239"):
        try:
            pr = s.get(f"{BASE}{cand}", timeout=30)
            out.append(f"  GET {cand} -> status={pr.status_code} len={len(pr.text)} "
                       f"含公众号={('公众号' in pr.text) or ('文章' in pr.text)}")
            html_extra = pr.text
            if mp_links := sorted(set(re.findall(r'/web/[a-zA-Z0-9_\-/]*MP_WXS_\d+', html_extra))):
                out.append(f"  [SSR公众号路由] {mp_links[:10]}")
            if "mp/articles" in html_extra:
                out.append(f"  [!!] 页面HTML直接含 mp/articles 调用")
        except Exception as e:
            out.append(f"  GET {cand} err {e}")

# 2) 收集 JS 入口
srcs = set()
for pat in (r'<script[^>]+src=["\']([^"\']+)["\']',
            r'<link[^>]+rel="modulepreload"[^>]+href=["\']([^"\']+)["\']',
            r'<link[^>]+rel="preload"[^>]+as="script"[^>]+href=["\']([^"\']+)["\']'):
    for m in re.finditer(pat, html):
        srcs.add(m.group(1))
srcs = [x for x in srcs if x.endswith(".js") and not x.startswith("data:")]
out.append(f"发现 {len(srcs)} 个入口 JS: {[x[:70] for x in srcs[:10]]}")
if not srcs:
    print("\n".join(out))
    open("scripts/probe_result.txt", "w", encoding="utf-8").write("\n".join(out))
    raise SystemExit

# 3) BFS 抓 chunk，找关键词
keywords = ["mp/articles", "mp/content", "/web/mp/", "x-wr-ticket", "wr-ticket",
            "ticket", "bookId", "shelf/sync", "mpList", "mp_list", "articles"]
hits = {}
seen = set()
queue = [(src, 0, src) for src in srcs]
total = 0
while queue and total < 600:
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
    if dep < 4:
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
            start = max(0, m.start() - 120)
            end = min(len(text), m.end() + 200)
            snippet = re.sub(r"\s+", " ", text[start:end])
            key = (kw, snippet[:60])
            hits.setdefault(kw, [])
            if key not in hits[kw]:
                hits[kw].append((ref[:70], snippet))

out.append(f"已抓取 {total} 个 JS")
if not hits:
    out.append("(全部 JS 均未命中接口/票证关键词)")
else:
    for kw, items in hits.items():
        out.append(f"\n--- 命中 {kw!r}（{len(items)} 处） ---")
        for src, snippet in items[:8]:
            out.append(f"  [{src}]\n    ...{snippet}...")

res = "\n".join(out)
open("scripts/probe_result.txt", "w", encoding="utf-8").write(res)
print(res)
