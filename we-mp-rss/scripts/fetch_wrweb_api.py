# -*- coding: utf-8 -*-
"""探测（第15轮）：4 个公众号逐一验证 getProgress->content 完整链路。

前置：static/weread_cookies.json 存在。
"""
import json
import os
import re
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEREAD = "https://weread.qq.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0")

data = json.load(open(os.path.join(ROOT, "static", "weread_cookies.json"),
                      encoding="utf-8"))
jar = data["jar"]
cookie_str = "; ".join(f"{k}={v}" for k, v in jar.items())

s = requests.Session()
s.headers.update({"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9",
                  "Cookie": cookie_str})

books = ["MP_WXS_3289811205", "MP_WXS_3556030239",
         "MP_WXS_3012726261", "MP_WXS_3084116771"]

for bid in books:
    print(f"\n{'='*60}\n### {bid}")
    # cover
    try:
        r = s.get(WEREAD + "/web/mp/cover", params={"bookId": bid}, timeout=20)
        cov = r.json()
        print(f"  cover: name={cov.get('name')} title={str(cov.get('title'))[:40]}")
        rid_cov = cov.get("reviewId", "")
        print(f"         reviewId={rid_cov}")
    except Exception as e:
        print(f"  cover err {e}")
        continue
    # getProgress
    try:
        r = s.get(WEREAD + "/web/book/getProgress", params={"bookId": bid}, timeout=20)
        prog = r.json()
        rid_prog = (prog.get("book") or {}).get("reviewId", "")
        print(f"  progress reviewId={rid_prog}")
    except Exception as e:
        print(f"  progress err {e}")
        rid_prog = ""
    # content(progress reviewId)
    for label, rid in [("cover", rid_cov), ("progress", rid_prog)]:
        if not rid:
            continue
        try:
            r = s.get(WEREAD + "/web/mp/content", params={"reviewId": rid}, timeout=25)
            html = r.text
            # 判断正文特征
            ok = any(k in html for k in ["js_content", "rich_media_content",
                                          "contentNoEncode", "msg_title"])
            banned = "已被屏蔽" in html or "屏蔽" in html
            deleted = "已被发布者删除" in html or "此内容因违规" in html
            title_m = re.search(r"property=\"og:title\" content=\"([^\"]+)\"", html)
            print(f"  content[{label}] status={r.status_code} len={len(html)} "
                  f"正文={ok} 屏蔽={banned} 删除={deleted} "
                  f"title={title_m.group(1)[:40] if title_m else '-'}")
        except Exception as e:
            print(f"  content[{label}] err {e}")
