import random
import time
from core.print import print_warning
def Wait(min=10,max=60,tips:str=""):
        wait=random.randint(min,max)
        print_warning(f"{tips}  等待{wait}秒后继续...")
        time.sleep(wait)