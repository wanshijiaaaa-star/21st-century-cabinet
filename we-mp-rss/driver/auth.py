import threading
import asyncio
from core.print import print_warning
from driver.base import WX_InterFace
import os
import portalocker
from core.task import TaskScheduler
from driver.success import Success

def auth():
    def run_auth():
        wx = WX_InterFace()
        # 在新的事件循环中运行异步方法
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(wx.switch_account())
        finally:
            loop.close()

    thread = threading.Thread(target=run_auth)
    thread.start()
    thread.join()  # 可选：等待完成
def start_auth_service():    
    # from driver.wx_api import login_with_token
    # login_with_token()
    if str(os.getenv('WE_RSS.AUTH',False))=="True":
        print_warning("启动授权定时任务")
        auth_task=TaskScheduler()
        auth_task.clear_all_jobs()
        print("是否开启调试模式:",str(os.getenv('DEBUG',False)))
        if str(os.getenv('DEBUG',False))=="True":
            auth_task.add_cron_job(auth, "*/10 * * * *",tag="授权定时更新")
        else:
            auth_task.add_cron_job(auth, "0 0 */1 * *",tag="授权定时更新")
        auth_task.start()