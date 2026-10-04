
import os
import sys
import asyncio

# Windows 需要使用 ProactorEventLoop 以支持 Playwright 子进程
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from core.config import cfg
print(f"认证方式：Web认证={bool(cfg.get('server.auth_web', False))}")
if bool(cfg.get("server.auth_web", False)) == True:
    from driver.wx import WX_API 
    from driver.wx import Wx as WX_InterFace
else:
    from driver.wx_api import WeChat_api as WX_API
    from driver.wx_api import WeChatAPI as WX_InterFace
