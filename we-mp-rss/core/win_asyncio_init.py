"""
Windows asyncio 事件循环策略初始化模块

必须在所有其他模块之前导入，以确保事件循环策略正确设置。
"""
import sys
import asyncio

# Windows 需要使用 ProactorEventLoop 以支持 Playwright 子进程
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
