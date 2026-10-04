# -*- coding: utf-8 -*-
"""查看 /web/mp/reader/info 完整响应 + /web/mp/content 正文验证"""
import json
import re
import sys

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

# reader/info 完整响应
try:
    r = requests.get(BASE + "/web/mp/reader/info", params={"bookId": BOOK}, headers=H, timeout=20)
    out.append(f"reader/info: HTTP {r.status_code} len={len(r.text)}")
    try:
        j = r.json()
        out.append(json.dumps(j, ensure_ascii=False, indent=2)[:3000])
        # 提取关键字段
        if isinstance(j, dict):
            out.append("\n=== 顶层字段 ===")
            out.append(str(list(j.keys())))
            for k, v in j.items():
                if isinstance(v, list):
                    out.append(f"  {k}: list[{len(v)}] 首个={json.dumps(v[0], ensure_ascii=False)[:200] if v else '-'}")
                elif isinstance(v, dict):
                    out.append(f"  {k}: dict keys={list(v.keys())[:15]}")
    except Exception:
        out.append(f"  (non-json) {r.text[:800]}")
except Exception as e:
    out.append(f"reader/info ERR {e}")

# 用 cover 的 reviewId 验证正文接口
rid = "MP_WXS_3556030239_aPVFCyffYEDN7MOdAzywJg"
for path in ("/web/mp/content", "/api/mp/content"):
    try:
        r = requests.get(BASE + path, params={"reviewId": rid},
                         headers={**H, "Accept": "text/html,*/*"}, timeout=20)
        ok = any(k in r.text for k in ("js_content", "rich_media_content", "contentNoEncode"))
        out.append(f"\n{path}?reviewId -> HTTP {r.status_code} len={len(r.text)} 正文={ok}")
        if ok:
            title = re.search(r'property="og:title" content="([^"]+)"', r.text)
            out.append(f"  title={title.group(1)[:60] if title else '-'}")
    except Exception as e:
        out.append(f"{path} ERR {e}")

res = "\n".join(out)
open("scripts/probe_result.txt", "w", encoding="utf-8").write(res)
print(res)
