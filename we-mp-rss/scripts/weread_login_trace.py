"""微信读书扫码登录抓包脚本：定位登录成功后浏览器实际发生的请求。

用途：排查「扫码登录成功但 Cookie 验证失败(-2012)」。微信读书新版把
wr_skey 设为 8 字符短值（= accessToken），真正的长令牌是 refreshToken
（= wr_rt 的 URL 解码值）。浏览器登录后可能还会调用「换令牌/刷新」接口，
本脚本用 Playwright 打开微信读书，等待扫码，登录成功后打印：

  1. 登录过程中浏览器发出的 auth / token / mp 相关请求（URL、POST 体、
     请求 Cookie）——据此可确定是否存在刷新接口及其地址；
  2. 登录后最终有效 Cookie 完整值——可直接填回 wx.lic，或据此修正
     driver/weread_qr.py 的 Cookie 构建逻辑。

用法:
    python scripts/weread_login_trace.py

依赖: pip install playwright && playwright install chromium
"""
import sys
import time
import json
import argparse
import tempfile

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("未安装 playwright，请执行: pip install playwright && playwright install chromium")

WEREAD = "https://weread.qq.com"
ARTICLE_URL = WEREAD + "/web/mp/articles"


def verify_cookie(cookie_str: str) -> bool:
    """用 weread.qq.com/web/mp/articles 验证 Cookie 有效性（项目同款方案）。"""
    try:
        import requests
    except ImportError:
        return True
    try:
        r = requests.get(
            ARTICLE_URL,
            params={"bookId": "MP_WXS_3528995129", "offset": 0},
            headers={
                "Cookie": cookie_str,
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Referer": WEREAD + "/",
            },
            timeout=20,
        )
        j = r.json()
        code = j.get("errCode", j.get("errcode", 0))
        return not code
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="微信读书扫码登录抓包")
    parser.add_argument("--profile", default=None, help="持久化 profile 目录（默认系统临时目录）")
    parser.add_argument("--timeout", type=int, default=600, help="等待扫码最长秒数（默认 600）")
    args = parser.parse_args()

    profile_dir = args.profile or tempfile.mkdtemp(prefix="weread-trace-")
    captured = []

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            profile_dir,
            headless=False,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = context.new_page()

        def on_request(req):
            url = req.url
            low = url.lower()
            if ("/api/auth" in low or "/auth/" in low or "token" in low
                    or "web/mp/articles" in low or "renewal" in low
                    or "/web/login" in low):
                cookie = req.headers.get("cookie", "")
                captured.append({
                    "method": req.method,
                    "url": url,
                    "post": (req.post_data or "")[:300],
                    "cookie_len": len(cookie),
                    "cookie_head": cookie[:120],
                })

        def on_response(resp):
            # 捕获 renewal/登录相关响应的 Set-Cookie，看服务器下发了什么新令牌
            low = resp.url.lower()
            if "renewal" in low or "getLoginInfo" in low or "/web/login" in low:
                set_cookie = resp.headers.get("set-cookie", "")
                if set_cookie:
                    captured.append({
                        "method": "RESP",
                        "url": resp.url,
                        "status": resp.status,
                        "set_cookie": set_cookie[:300],
                    })

        page.on("request", on_request)
        page.on("response", on_response)
        page.goto(WEREAD + "/", wait_until="domcontentloaded", timeout=60000)
        print("[trace] 请在打开的 Chrome 窗口扫码登录微信读书（最长等待 "
              f"{args.timeout} 秒）...")

        deadline = time.time() + args.timeout
        logged_in = False
        while time.time() < deadline:
            cks = context.cookies(WEREAD)
            ck_str = "; ".join(f"{c['name']}={c['value']}" for c in cks)
            if "wr_vid=" in ck_str and verify_cookie(ck_str):
                logged_in = True
                break
            time.sleep(3)

        if not logged_in:
            print("[trace] 等待扫码超时，未拿到有效登录态。")
        else:
            print("\n===== 登录成功！auth/token 相关请求记录（按时间） =====")
            if not captured:
                print("  （未捕获到 auth/token 请求）")
            for c in captured:
                if c.get("method") == "RESP":
                    print(f"[RESP {c.get('status')}] {c['url']}")
                    print(f"    Set-Cookie: {c.get('set_cookie')}")
                    continue
                print(f"[{c['method']}] {c['url']}")
                print(f"    post={c['post']!r}")
                print(f"    cookie(len={c['cookie_len']}): {c['cookie_head']}...")

            print("\n===== 最终有效 Cookie（可直接填回 wx.lic） =====")
            cks = context.cookies(WEREAD)
            full = "; ".join(f"{c['name']}={c['value']}" for c in cks)
            print(full)

            print("\n===== Cookie 明细 =====")
            for c in cks:
                v = c["value"]
                shown = v[:20] + ("..." if len(v) > 20 else "")
                print(f"  {c['name']} = {shown} (len={len(v)})")

        context.close()


if __name__ == "__main__":
    main()
