# -*- coding: utf-8 -*-
"""看 /api/mp/cover 完整字段 + /web/mp/reader 页面 + Encryption 加密逻辑"""
import json
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

H = {"User-Agent": UA, "Accept": "application/json, text/plain, */*",
     "Accept-Language": "zh-CN,zh;q=0.9", "Origin": "https://weread.qq.com",
     "Referer": "https://weread.qq.com/", "Cookie": cookie}

BOOK = "MP_WXS_3556030239"
out = []

# 1) cover 完整响应
try:
    r = requests.get(BASE + "/api/mp/cover", params={"bookId": BOOK}, headers=H, timeout=20)
    out.append(f"cover: HTTP {r.status_code}")
    out.append(json.dumps(r.json(), ensure_ascii=False, indent=2)[:1500])
except Exception as e:
    out.append(f"cover ERR {e}")

# 2) reader 页面（不带加密参数 / 变体）
for cand in ("/web/mp/reader", "/web/mp/reader?bookId=" + BOOK,
             "/web/mp/reader/info?bookId=" + BOOK):
    try:
        r = requests.get(BASE + cand, headers={**H, "Accept": "text/html,*/*"}, timeout=20)
        out.append(f"\nGET {cand} -> HTTP {r.status_code} len={len(r.text)}")
        # 找接口线索
        for kw in ("/api/", "/web/", "mp/articles", "review", "article", "ticket"):
            if kw in r.text:
                out.append(f"  含 {kw!r}")
    except Exception as e:
        out.append(f"GET {cand} ERR {e}")

# 3) 抓 Encryption 实现（DIOuE9ph.js 及依赖）
try:
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
    total = 0
    enc_found = []
    while queue and total < 400:
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
        if "Encryption" in text or ("encrypt" in text and "decrypt" in text):
            for m in re.finditer(r'.{80}(?:Encryption|encrypt).{200}', text):
                enc_found.append((src[-45:], re.sub(r"\s+", " ", m.group(0))))
    out.append(f"\n=== Encryption 实现（抓 {total} JS，{len(enc_found)} 命中） ===")
    for src, snip in enc_found[:8]:
        out.append(f"  [{src}]\n    {snip}")
except Exception as e:
    out.append(f"Encryption 抓取失败: {e}")

res = "\n".join(out)
open("scripts/probe_result.txt", "w", encoding="utf-8").write(res)
print(res)
