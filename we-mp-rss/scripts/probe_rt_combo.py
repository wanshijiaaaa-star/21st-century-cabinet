# -*- coding: utf-8 -*-
"""交叉组合：当前有效 cookie + 旧完整 jar 的 wr_rt/wr_gid，定位 mp/articles -2041 根源"""
import json
import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0")
FULL = {
    "User-Agent": UA,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Origin": "https://weread.qq.com",
    "Referer": "https://weread.qq.com/",
}

# 当前 wx.lic（有效，缺 wr_rt）
raw = open("data/wx.lic", encoding="utf-8").read()
cur = {}
for line in raw.splitlines():
    if "cookie:" in line and "wr_" in line:
        c = line.split("cookie:", 1)[1].strip().strip("'").strip()
        for part in c.split(";"):
            k, _, v = part.strip().partition("=")
            if k:
                cur[k] = v

# 旧完整 jar（含 wr_rt / wr_gid）
old = {}
try:
    d = json.load(open("static/weread_cookies.json", encoding="utf-8"))
    old = d.get("jar", {})
    print("old jar keys:", list(old.keys()))
except Exception as e:
    print("read old jar failed:", e)

print("cur jar keys:", list(cur.keys()))

BOOK = "MP_WXS_3556030239"
combos = [
    ("cur", dict(cur)),
    ("cur+rt(old)", {**cur, "wr_rt": old.get("wr_rt", "")}),
    ("cur+rt(old)+gid(old)", {**cur, "wr_rt": old.get("wr_rt", ""), "wr_gid": old.get("wr_gid", "")}),
    ("cur+rt(old)+gid(old)+fp(old)", {**cur, "wr_rt": old.get("wr_rt", ""),
                                      "wr_gid": old.get("wr_gid", ""), "wr_fp": old.get("wr_fp", "")}),
    ("old-full", dict(old)),
]

out = []
for label, ck in combos:
    h = dict(FULL)
    h["Cookie"] = "; ".join(f"{k}={v}" for k, v in ck.items() if v)
    lines = []
    for path, params in (
        ("/web/shelf/sync", {"userVid": "", "synckey": 0}),
        ("/web/mp/articles", {"bookId": BOOK, "offset": 0}),
    ):
        try:
            r = requests.get("https://weread.qq.com" + path, params=params,
                             headers=h, timeout=20)
            j = r.json()
            code = j.get("errCode", j.get("errcode", 0))
            n = len(j.get("reviews") or [])
            lines.append(f"    {path} HTTP {r.status_code} code={code} reviews={n} "
                         f"body={str(j)[:90]!r}")
        except Exception as e:
            lines.append(f"    {path} ERR {e}")
    out.append(f"[{label}] jar={list(ck.keys())}\n" + "\n".join(lines))

print("\n\n".join(out))
open("scripts/probe_result.txt", "w", encoding="utf-8").write("\n\n".join(out))
