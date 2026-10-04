# -*- coding: utf-8 -*-
"""微信读书扫码登录诊断脚本（一次性排查 -2012「登录超时」）。

用法:
    python scripts/weread_scan_diag.py

流程:
1. 自动获取 uid 并生成二维码(static/weread_qrcode.png)，控制台提示扫码；
2. 用与浏览器一致的 /api/auth/getLoginInfo 轮询，扫码成功后打印
   getLoginInfo 原始 Set-Cookie 与 cookie jar（不做任何令牌探测/覆盖）；
3. 按 papers3-weread 参考实现的"最小 Cookie"组合（wr_vid + wr_skey + wr_rt，
   不带 wr_ql）逐个调用真实接口(shelf/sync、/web/mp/articles)验证，
   找出哪个组合/字段导致 -2012；
4. 尝试多种激活路径（首页刷新、user/detail、renewal 变体），观察服务端
   是否补发新的完整 Cookie；
5. 激活后重跑验证矩阵。

不修改任何业务代码，扫码结果只用于诊断打印。
"""

import os
import re
import sys
import time
import json
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import requests

from driver.weread_qr import WereadQRLogin, WEREAD_BASE, WEREAD_API

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0")

HEADERS_FULL = {
    "User-Agent": UA,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Origin": "https://weread.qq.com",
    "Referer": "https://weread.qq.com/",
}


def _mask(v):
    if isinstance(v, str):
        if len(v) <= 8:
            return v
        return f"str(len={len(v)}) {v[:6]}...{v[-4:]}"
    return v


def _all_set_cookies(resp):
    """取响应全部 Set-Cookie 头（requests 顶层 headers 只保留最后一条）。"""
    try:
        if resp.raw is not None:
            return resp.raw.headers.getlist("Set-Cookie") or []
    except Exception:
        pass
    sc = resp.headers.get("Set-Cookie")
    return [sc] if sc else []


def _short_desc(resp):
    scs = _all_set_cookies(resp)
    set_cookie = " | ".join(s[:120] for s in scs) or "(none)"
    try:
        j = resp.json()
        if isinstance(j, dict):
            body = json.dumps({k: _mask(v) for k, v in list(j.items())[:6]},
                              ensure_ascii=False, default=str)
        else:
            body = str(j)[:150]
    except Exception:
        body = f"(raw {resp.text[:120]!r})"
    return f"status={resp.status_code} body={body} Set-Cookie={set_cookie!r}"


def _parse_set_cookie(header):
    """从单个 Set-Cookie 头解析出 (name, value)。"""
    if not header:
        return None
    head = header.split(";", 1)[0]
    if "=" not in head:
        return None
    k, _, v = head.partition("=")
    return k.strip(), v.strip()


DEFAULT_MP_BOOK_ID = "MP_WXS_3528995129"


def _get_subscribed_mp_books(cookies, headers):
    """用 web 域 shelf/sync 获取已订阅公众号（MP_WXS_*）列表。

    参考 steptian/weread-mp：GET https://weread.qq.com/web/shelf/sync
    userVid 必须传空字符串（非空反而会触发 -2012）。返回 (ok, [bookId, ...])。
    """
    h = dict(headers)
    h["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
    try:
        r = requests.get(f"{WEREAD_BASE}/web/shelf/sync",
                         params={"userVid": "", "synckey": 0},
                         headers=h, timeout=20)
        try:
            j = r.json()
        except Exception:
            return False, []
        code = j.get("errCode", j.get("errcode", 0))
        if code:
            return False, []
        books = j.get("books", []) or []
        mps = [b.get("bookId") for b in books
               if isinstance(b.get("bookId"), str) and b["bookId"].startswith("MP_WXS_")]
        return True, mps
    except Exception:
        return False, []


def _verify_mp(cookies, headers, book_id=DEFAULT_MP_BOOK_ID):
    h = dict(headers)
    h["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
    try:
        r = requests.get(f"{WEREAD_BASE}/web/mp/articles",
                         params={"bookId": book_id, "offset": 0},
                         headers=h, timeout=20)
        try:
            j = r.json()
            code = j.get("errCode", j.get("errcode", 0))
            ok = (r.status_code == 200 and not code and
                  ("reviews" in j or "articles" in j or "synckey" in j or j.get("bookId")))
            return ok, f"mp/articles({book_id}) " + _short_desc(r)
        except Exception:
            return False, f"mp/articles({book_id}) non-json " + _short_desc(r)
    except Exception as e:
        return False, f"mp/articles({book_id}) err {e}"


def _verify_shelf(cookies, headers):
    """web 域书架接口（公众号列表在 books 里），userVid 传空字符串。"""
    h = dict(headers)
    h["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
    try:
        r = requests.get(f"{WEREAD_BASE}/web/shelf/sync",
                         params={"userVid": "", "synckey": 0},
                         headers=h, timeout=20)
        try:
            j = r.json()
            code = j.get("errCode", j.get("errcode", 0))
            books = j.get("books", []) or []
            mps = [b.get("bookId") for b in books
                   if isinstance(b.get("bookId"), str) and b["bookId"].startswith("MP_WXS_")]
            ok = (r.status_code == 200 and not code and "books" in j)
            extra = f" (MP_WXS_ x{len(mps)}: {', '.join(mps[:3])})" if mps else ""
            return ok, f"web/shelf/sync " + _short_desc(r) + extra
        except Exception:
            return False, "web/shelf/sync non-json " + _short_desc(r)
    except Exception as e:
        return False, f"web/shelf/sync err {e}"


def _verify_all(label, cookies, headers, book_id=DEFAULT_MP_BOOK_ID):
    ok1, d1 = _verify_mp(cookies, headers, book_id)
    ok2, d2 = _verify_shelf(cookies, headers)
    flag = "OK " if (ok1 or ok2) else "FAIL"
    print(f"  [{flag}] {label}")
    print(f"       {d1}")
    print(f"       {d2}")
    return ok1 or ok2


def _run_verify_matrix(combos, book_id=DEFAULT_MP_BOOK_ID):
    print("\n==== 验证矩阵（完整请求头） ====")
    for label, ck in combos:
        _verify_all(label, ck, HEADERS_FULL, book_id)
    print("\n==== 验证矩阵（仅 User-Agent 请求头，papers3 风格） ====")
    for label, ck in combos:
        _verify_all(label + " [only-UA]", ck, {"User-Agent": UA}, book_id)


def _probe_mp_variants(cookies, book_id, vid=""):
    """定位 web/mp/articles 返回 -2041 的真实原因：参数/方法/头/UA 变体 + 多订阅号验证。

    认证已由 shelf/sync 证明通过，-2041 必是接口调用方式问题，这里穷举常见变体。
    """
    print("\n==== mp/articles 变体矩阵（定位 -2041） ====")
    cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
    chrome148 = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                 "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
    minimal = {
        "User-Agent": chrome148,
        "Accept": "application/json, text/plain, */*",
    }
    full = {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Origin": "https://weread.qq.com",
        "Referer": "https://weread.qq.com/",
    }
    base = {"bookId": book_id, "offset": 0}

    cases = []

    def add(label, method, headers, params, data=None, json_body=None):
        cases.append((label, method, headers, params, data, json_body))

    # 参数变体（GET + 完整头）
    add("V1 base", "GET", full, base)
    add("V2 +count=20", "GET", full, {**base, "count": 20})
    add("V3 +count=10", "GET", full, {**base, "count": 10})
    add("V4 +listType=2", "GET", full, {**base, "listType": 2})
    add("V5 +listType=1", "GET", full, {**base, "listType": 1})
    add("V6 +count20+listType2", "GET", full, {**base, "count": 20, "listType": 2})
    add("V7 no-offset", "GET", full, {"bookId": book_id})
    add("V8 +uid=<vid>", "GET", full, {**base, "uid": vid})
    # 方法变体
    add("V9 POST form", "POST", full, {}, data={"bookId": book_id, "offset": 0})
    add("V10 POST json", "POST", full, {}, json_body={"bookId": book_id, "offset": 0})
    # 头 / UA / bookId 变体
    add("V11 最小头 Chrome148", "GET", minimal, base)
    add("V12 完整头 Chrome148", "GET", {**full, "User-Agent": chrome148}, base)
    add("V13 纯数字bookId", "GET", full, {"bookId": str(book_id).replace("MP_WXS_", ""), "offset": 0})
    add("V14 带x-wr-ticket头", "GET", {**full, "x-wr-ticket": ""}, base)
    add("V15 无Origin/Referer", "GET",
        {k: v for k, v in full.items() if k not in ("Origin", "Referer")}, base)
    add("V16 无Cookie", "GET", full, base)
    add("V17 +synckey=0", "GET", full, {**base, "synckey": 0})
    add("V18 +listType2+count20+synckey", "GET", full,
        {**base, "count": 20, "listType": 2, "synckey": 0})
    add("V19 ticket=wr_skey", "GET",
        {**full, "x-wr-ticket": cookies.get("wr_skey", "")}, base)
    add("V20 +subType=1", "GET", full, {**base, "subType": 1})

    for label, method, headers, params, data, json_body in cases:
        h = dict(headers)
        if label != "V16 无Cookie":
            h["Cookie"] = cookie_str
        try:
            if method == "POST":
                r = requests.post(f"{WEREAD_BASE}/web/mp/articles", params=params,
                                  data=data, json=json_body, headers=h, timeout=20)
            else:
                r = requests.get(f"{WEREAD_BASE}/web/mp/articles", params=params,
                                 headers=h, timeout=20)
            try:
                j = r.json()
                code = j.get("errCode", j.get("errcode", 0))
                n_reviews = len(j.get("reviews") or [])
            except Exception:
                code = "non-json"
                n_reviews = 0
            mark = ">>> OK" if code == 0 else ""
            extra = ""
            if code == "non-json":
                extra = f"  status={r.status_code} body={r.text[:200]!r}"
            print(f"  {label:<26} {method:<4} code={code} reviews={n_reviews} {mark}{extra}")
        except Exception as e:
            print(f"  {label:<26} {method:<4} err {e}")

    print("\n  --- 全部真实订阅号逐一验证 base GET ---")
    sub_ok2, sub_mps2 = _get_subscribed_mp_books(cookies, full)
    for bid in sub_mps2:
        h = dict(full)
        h["Cookie"] = cookie_str
        try:
            r = requests.get(f"{WEREAD_BASE}/web/mp/articles",
                             params={"bookId": bid, "offset": 0}, headers=h, timeout=20)
            j = r.json()
            code = j.get("errCode", j.get("errcode", 0))
            n_reviews = len(j.get("reviews") or [])
            mark = ">>> OK" if code == 0 else ""
            print(f"  {bid:<26} code={code} reviews={n_reviews} {mark}")
        except Exception as e:
            print(f"  {bid:<26} err {e}")

    print("\n  --- 其它可能路径探测（base GET） ---")
    for alt_path in ("/mp/articles", "/wr/mp/articles", "/web/mp/feeds",
                     "/web/feed/mp", "/web/mp/articles/page"):
        h = dict(full)
        h["Cookie"] = cookie_str
        try:
            r = requests.get(f"{WEREAD_BASE}{alt_path}", params=base,
                             headers=h, timeout=20)
            try:
                j = r.json()
                code = j.get("errCode", j.get("errcode", 0))
                body = str(j)[:120]
            except Exception:
                code = "non-json"
                body = r.text[:120]
            mark = ">>> OK" if code == 0 else ""
            print(f"  {alt_path:<24} code={code} {mark} body={body!r}")
        except Exception as e:
            print(f"  {alt_path:<24} err {e}")


def _extract_mp_api_from_frontend(cookie_str=""):
    """下载 weread.qq.com 前端 JS（含懒加载 chunk），提取 /web/mp/ 相关接口与 ticket 逻辑。

    首页是 Nuxt3(data-capo)，入口 JS 只有 4 个，业务代码在懒加载 chunk 里，
    因此必须递归 BFS 抓取全部 chunk。同时分析 SSR HTML 里的公众号路由与内嵌数据。
    """
    from urllib.parse import urljoin

    print("\n==== 前端 JS 接口提取（weread.qq.com 真实调用方式） ====")
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    if cookie_str:
        s.headers["Cookie"] = cookie_str
    try:
        r = s.get(f"{WEREAD_BASE}/", timeout=30)
        html = r.text
    except Exception as e:
        print(f"  [!] 首页获取失败: {e}")
        return

    # 1) 首页 SSR HTML 线索
    print(f"  首页 HTML {len(html)}B")
    mp_links = sorted(set(re.findall(r'/web/[a-zA-Z0-9_\-/]*MP_WXS_\d+', html)))
    if mp_links:
        print(f"  [SSR公众号路由] 前20: {mp_links[:20]}")
    nux_data = re.findall(r'__NUXT_DATA__|window\.__NUXT__', html)
    if nux_data:
        print(f"  [SSR内嵌数据] 存在 {len(nux_data)} 处 __NUXT__ 标记")

    # 2) 收集 JS 入口（script src + modulepreload + preload script）
    srcs = set()
    for pat in (r'<script[^>]+src=["\']([^"\']+)["\']',
                r'<link[^>]+rel="modulepreload"[^>]+href=["\']([^"\']+)["\']',
                r'<link[^>]+rel="preload"[^>]+as="script"[^>]+href=["\']([^"\']+)["\']'):
        for m in re.finditer(pat, html):
            srcs.add(m.group(1))
    srcs = [x for x in srcs if x.endswith(".js") and not x.startswith("data:")]
    print(f"  发现 {len(srcs)} 个入口 JS: {[x[:70] for x in srcs[:10]]}")
    if not srcs:
        print("  (未发现 JS 入口，需人工检查首页 HTML)")
        return

    # 3) BFS 递归抓取全部 chunk
    keywords = ["mp/articles", "mp/content", "/web/mp/", "x-wr-ticket", "wr-ticket",
                "ticket", "bookId", "shelf/sync", "mpList", "mp_list"]
    hits = {}
    seen = set()
    queue = [(src, 0, src) for src in srcs]
    total = 0
    while queue and total < 800:
        src, dep, ref = queue.pop(0)
        if src in seen:
            continue
        seen.add(src)
        url = urljoin(f"{WEREAD_BASE}/", src)
        try:
            rr = s.get(url, timeout=25)
            if rr.status_code != 200 or len(rr.content) > 10_000_000:
                continue
            text = rr.text
        except Exception:
            continue
        total += 1
        # 提取 chunk 引用（下一层递归）
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
    print(f"  已抓取 {total} 个 JS（含入口与懒加载 chunk）")
    if not hits:
        print("  (全部 JS 均未命中接口/票证关键词 —— 公众号模块可能已从新版前端移除)")
        return
    for kw, items in hits.items():
        print(f"\n  --- 命中 {kw!r}（{len(items)} 处） ---")
        for src, snippet in items[:10]:
            print(f"  [{src}]\n    ...{snippet}...")

    # 4) 若 SSR HTML 含公众号路由，直接 GET 该页，SSR 会带着已渲染数据返回
    if mp_links:
        print("\n  --- SSR 公众号页面直接抓取 ---")
        for link in mp_links[:3]:
            url = f"{WEREAD_BASE}{link}"
            try:
                pr = s.get(url, timeout=30)
                body = pr.text
                has_article = re.search(r"公众号|文章|订阅", body)
                print(f"  GET {link} -> status={pr.status_code} len={len(body)} "
                      f"含文章关键字={bool(has_article)}")
                if has_article:
                    m = re.search(r'MP_WXS_\d+', body)
                    print(f"    页面内公众号ID: {m.group(0) if m else '-'}")
            except Exception as e:
                print(f"  GET {link} -> err {e}")


_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_COOKIE_FILE = os.path.join(_PROJECT_ROOT, "static", "weread_cookies.json")


def _qr_login(session):
    """扫码登录，返回 (jar, vid, at, rt)；失败返回 (None,)*4。"""
    manager = WereadQRLogin()
    manager._reset()
    uid = manager._get_login_uid()
    if not uid:
        print("[DIAG] 获取 UID 失败")
        return None, None, None, None
    manager._uid = uid
    manager._generate_qr_image(uid)
    print(f"[DIAG] 请用微信扫描二维码: {manager._qr_code_path}")
    print("[DIAG] 等待扫码确认（最长 300s，请勿重复扫码）...")

    login_data = None
    raw_set_cookies = []
    deadline = time.time() + 300
    while time.time() < deadline:
        resp = session.get(f"{WEREAD_BASE}/api/auth/getLoginInfo",
                           params={"uid": uid, "otp": ""}, timeout=70)
        try:
            data = resp.json()
        except Exception:
            data = {}
        if data.get("succeed"):
            login_data = data
            # requests 的 CaseInsensitiveDict 无 getlist，改用底层 urllib3 头
            try:
                raw_set_cookies = resp.raw.headers.getlist("Set-Cookie") or []
            except Exception:
                raw_set_cookies = []
            if not raw_set_cookies and resp.headers.get("Set-Cookie"):
                raw_set_cookies = [resp.headers["Set-Cookie"]]
            break
        time.sleep(2)
    if not login_data:
        print("[DIAG] 扫码超时")
        return None, None, None, None

    print("\n==== getLoginInfo 成功响应（字段清单，值脱敏） ====")
    for k, v in login_data.items():
        print(f"  {k} = {_mask(str(v)) if isinstance(v, str) else v!r}")
    print("\n==== getLoginInfo 响应原始 Set-Cookie ====")
    for h in raw_set_cookies:
        print(f"  SC: {h[:200]!r}")

    # 原始 jar（仅来自 Set-Cookie，不覆盖）
    jar = {}
    for h in raw_set_cookies:
        p = _parse_set_cookie(h)
        if p:
            jar[p[0]] = p[1]
    for c in session.cookies:
        jar.setdefault(c.name, c.value)

    vid = login_data.get("webLoginVid") or login_data.get("vid") or ""
    at = login_data.get("accessToken", "")
    rt = login_data.get("refreshToken", "")
    print(f"\n==== 解析结果 ====")
    print(f"  vid={vid} accessToken={_mask(at)} refreshToken={_mask(rt)}")
    print(f"  jar: {', '.join(f'{k}={_mask(v)}' for k, v in jar.items())}")
    return jar, vid, at, rt


def _load_cached_cookies(cookie_file, session):
    """复用已保存登录态；wr_skey 失效则删缓存返回 (None,)*4。"""
    if not os.path.exists(cookie_file):
        return None, None, None, None
    try:
        with open(cookie_file, encoding="utf-8") as f:
            data = json.load(f)
        jar = data.get("jar", {})
        if not jar.get("wr_skey"):
            return None, None, None, None
        h = dict(HEADERS_FULL)
        h["Cookie"] = "; ".join(f"{k}={v}" for k, v in jar.items())
        r = session.get(f"{WEREAD_BASE}/web/shelf/sync",
                        params={"userVid": "", "synckey": 0}, headers=h, timeout=20)
        j = r.json()
        code = j.get("errCode", j.get("errcode", 0))
        if code in (0, -2012):
            if code == -2012:
                print("[DIAG] 缓存登录态已失效(-2012)，删除缓存重新扫码")
                os.remove(cookie_file)
                return None, None, None, None
            print(f"[DIAG] 复用缓存登录态（{cookie_file}），已订阅公众号 {j.get('bookCount', '?')} 个")
            return (jar, str(data.get("vid", "")),
                    data.get("access_token", ""), data.get("refresh_token", ""))
        print(f"[DIAG] 缓存登录态异常(code={code})，删除缓存重新扫码")
        os.remove(cookie_file)
    except Exception as e:
        print(f"[DIAG] 缓存读取失败({e})，重新扫码")
    return None, None, None, None


def _save_cached_cookies(cookie_file, jar, vid, at, rt):
    try:
        os.makedirs(os.path.dirname(cookie_file), exist_ok=True)
        with open(cookie_file, "w", encoding="utf-8") as f:
            json.dump({"jar": jar, "vid": vid, "access_token": at,
                       "refresh_token": rt, "saved_at": time.time()}, f,
                      ensure_ascii=False, indent=2)
        print(f"[DIAG] 登录态已缓存到 {cookie_file}")
    except Exception as e:
        print(f"[DIAG] 缓存保存失败: {e}")


def main():
    # ---------- 1) 扫码登录（优先复用缓存，避免每次重扫） ----------
    session = requests.Session()
    session.headers.update(HEADERS_FULL)
    jar, vid, at, rt = _load_cached_cookies(_COOKIE_FILE, session)
    if not jar:
        jar, vid, at, rt = _qr_login(session)
        if not jar:
            return
        _save_cached_cookies(_COOKIE_FILE, jar, vid, at, rt)
    uid = ""

    short = jar.get("wr_skey") or at
    rt_enc = quote(rt, safe="") if rt else ""

    # ---------- 3) 用 web 域 shelf/sync 获取真实订阅公众号 ----------
    print("\n==== 真实订阅公众号探测（web/shelf/sync, userVid=''） ====")
    sub_ok, sub_mps = _get_subscribed_mp_books(jar, HEADERS_FULL)
    print(f"  shelf_ok={sub_ok} 已订阅公众号 {len(sub_mps)} 个: {', '.join(sub_mps[:10]) or '(无)'}")
    if not sub_ok:
        print("  (提示: 若返回 -2012/-2041，可能是登录态无效或未订阅任何公众号)")
    book_id = sub_mps[0] if sub_mps else DEFAULT_MP_BOOK_ID

    # ---------- 4) 验证矩阵（用真实订阅号） ----------
    combos = [
        ("A.jar-raw(含wr_ql)", dict(jar)),
        ("B.vid+skey(短值)", {"wr_vid": str(vid), "wr_skey": short}),
        ("C.vid+skey(短值)+rt(enc)", {"wr_vid": str(vid), "wr_skey": short, "wr_rt": rt_enc}),
        ("D.vid+skey(短值)+rt(dec)", {"wr_vid": str(vid), "wr_skey": short, "wr_rt": rt}),
        ("E.vid+skey(短值)+rt(enc)+ql=1", {"wr_vid": str(vid), "wr_skey": short, "wr_rt": rt_enc, "wr_ql": "1"}),
        ("F.vid+skey(rt)+rt(enc)", {"wr_vid": str(vid), "wr_skey": rt, "wr_rt": rt_enc}),
        ("G.vid+skey(rt)+rt(dec)", {"wr_vid": str(vid), "wr_skey": rt, "wr_rt": rt}),
    ]
    _run_verify_matrix(combos, book_id)

    # ---------- 5) 激活路径（观察 Set-Cookie 补发） ----------
    print("\n==== 激活路径尝试（带登录 Cookie，观察 Set-Cookie 补发与 jar 变化） ====")
    act = requests.Session()
    act.headers.update(HEADERS_FULL)
    # 关键修复：注入 getLoginInfo 下发的登录 cookie，模拟浏览器登录后的 session，
    # 否则服务端把请求当游客处理，永不补发完整 cookie（此前 -2013 也由此导致）。
    for k, v in jar.items():
        act.cookies.set(k, v, domain="weread.qq.com", path="/")

    def _jar_str():
        return ", ".join(f"{c.name}={_mask(c.value)}" for c in act.cookies)

    activations = [
        ("GET / 首页", f"{WEREAD_BASE}/", None, None),
        ("GET /web/shelf", f"{WEREAD_BASE}/web/shelf", None, None),
        ("GET /web/confirm", f"{WEREAD_BASE}/web/confirm", {"uid": uid}, None),
        ("GET web/shelf/sync", f"{WEREAD_BASE}/web/shelf/sync",
         {"userVid": "", "synckey": 0}, None),
        ("POST renewal (无ql)", f"{WEREAD_BASE}/web/login/renewal", None,
         {"rq": "%2Fweb%2Fbook%2Fread"}),
        ("POST renewal (带ql)", f"{WEREAD_BASE}/web/login/renewal", None,
         {"rq": "%2Fweb%2Fbook%2Fread", "ql": True}),
    ]
    for label, url, params, post in activations:
        before = _jar_str()
        try:
            if post is not None:
                r = act.post(url, params=params, data=json.dumps(post, separators=(",", ":")),
                             timeout=20)
            else:
                r = act.get(url, params=params, timeout=20)
            print(f"[ACT] {label} -> {_short_desc(r)}")
            print(f"      jar-before: {before}")
            print(f"      jar-after : {_jar_str()}")
        except Exception as e:
            print(f"[ACT] {label} 异常: {e}")

    # ---------- 5) 激活后用更新后 jar 重跑验证 ----------
    new_jar = {c.name: c.value for c in act.cookies}
    print("\n==== 激活后最终 jar ====")
    print(f"  {', '.join(f'{k}={_mask(v)}' for k, v in new_jar.items())}")
    print("\n==== 激活后验证 ====")
    combos2 = [
        ("A2.act-jar", dict(new_jar)),
        ("C2.vid+skey(短值)+rt(enc)", {"wr_vid": str(vid), "wr_skey": short, "wr_rt": rt_enc}),
    ]
    for label, ck in combos2:
        _verify_all(label, ck, HEADERS_FULL, book_id)

    # ---------- 6) mp/articles 变体矩阵（定位 -2041） ----------
    _probe_mp_variants(new_jar, book_id, vid=str(vid))
    _extract_mp_api_from_frontend(
        "; ".join(f"{k}={v}" for k, v in new_jar.items()))

    print("\n[DIAG] 完成。请把以上输出发回分析。")


if __name__ == "__main__":
    main()
