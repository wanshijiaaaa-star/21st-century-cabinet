#!/usr/bin/env python3
"""宿主机入口：微信读书 Cookie 刷新（全部在本机完成，容器只消费结果）。

架构说明（关键）：
- 微信读书的登录态 profile 由 macOS 钥匙串加密。容器内是 Linux Chromium，**解密不了**
  宿主机写入的 profile，因此在容器内做 Cookie 刷新必然失败。
- 故所有浏览器操作（首次扫码 + 每日自动刷新）都放在**宿主机**用本机 Chrome 执行，
  刷新成功后把明文 Cookie 写回数据卷的 wx.lic。
- 容器（jobs/mps.add_job）不再启动浏览器，只读取 wx.lic 的明文 Cookie 同步文章。

用法：
    # 首次建立登录态 / 过期后重扫：弹可见窗口，手机扫码（默认 GUI 模式）
    python scripts/refresh_weread_cookie.py

    # 每日自动刷新（供 launchd 调用，无头、不弹窗、不等待扫码）：
    python scripts/refresh_weread_cookie.py --headless
"""
import os
import sys
import argparse

# 日志实时落盘（launchd 场景下 stdout 重定向为文件时避免全缓冲滞后）
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

# 让脚本能 import 项目的 core 包
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# 指向宿主机上容器挂载的数据卷 wx.lic（默认，可被环境变量覆盖）
os.environ.setdefault("WEREAD_LIC_PATH", "/Users/yangqing/wechat-rss-data/wx.lic")
# 持久化登录 profile 目录（同一物理数据卷）；由本机 Chrome 持有，宿主机刷新时复用
os.environ.setdefault("WEREAD_PROFILE_DIR", "/Users/yangqing/wechat-rss-data/weread-chrome-profile")

from core.weread_cookie_refresh import refresh_weread_cookie  # noqa: E402


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="微信读书 Cookie 刷新（宿主机）")
    parser.add_argument(
        "--headless", action="store_true",
        help="无头模式：每日自动刷新用，不弹窗、不等待扫码；登录态过期时直接返回失败",
    )
    args = parser.parse_args()
    ok = refresh_weread_cookie(verbose=True, headless_only=args.headless)
    sys.exit(0 if ok else 1)
