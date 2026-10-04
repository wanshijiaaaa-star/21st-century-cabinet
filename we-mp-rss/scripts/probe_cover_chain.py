# -*- coding: utf-8 -*-
"""实测 cover->getProgress->content 链路 + reviewId 对应的 bookmarklist"""
import json
import requests

raw = open("data/wx.lic", encoding="utf-8").read()
cookie = ""
for line in raw.splitlines():
    if "cookie:" in line and "wr_" in line:
        cookie = line.split("cookie:", 1)[1].strip().strip("'").strip()
        break

headers = {
    "Cookie": cookie,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Origin": "https://weread.qq.com",
    "Referer": "https://weread.qq.com/",
}

BOOK = "MP_WXS_3556030239"
out = []

# cover
try:
    r = requests.get("https://weread.qq.com/web/mp/cover", params={"bookId": BOOK},
                     headers=headers, timeout=20)
    cov = r.json()
    out.append(f"cover: HTTP {r.status_code} body={str(cov)[:300]}")
    rid_cov = cov.get("reviewId", "")
except Exception as e:
    out.append(f"cover ERR {e}")
    rid_cov = ""

# getProgress
rid_prog = ""
try:
    r = requests.get("https://weread.qq.com/web/book/getProgress", params={"bookId": BOOK},
                     headers=headers, timeout=20)
    prog = r.json()
    out.append(f"getProgress: HTTP {r.status_code} body={str(prog)[:300]}")
    rid_prog = (prog.get("book") or {}).get("reviewId", "")
except Exception as e:
    out.append(f"getProgress ERR {e}")

# 用 reviewId 查 bookmarklist（公众号文章划线可能在单篇文章 bookId 维度）
for label, rid in [("cover", rid_cov), ("progress", rid_prog)]:
    if not rid:
        continue
    for param_name in ("bookId", "reviewId"):
        try:
            r = requests.get("https://weread.qq.com/web/book/bookmarklist",
                             params={param_name: rid}, headers=headers, timeout=20)
            out.append(f"bookmarklist[{label}/{param_name}={rid[:30]}...] "
                       f"HTTP {r.status_code} body={r.text[:150]!r}")
        except Exception as e:
            out.append(f"bookmarklist[{label}/{param_name}] ERR {e}")

print("\n".join(out))
open("scripts/probe_result.txt", "w", encoding="utf-8").write("\n".join(out))
