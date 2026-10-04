from .model import *
from .base import WxGather
ga=WxGather()
def search_Biz(kw:str="",limit=5,offset=0):
    return ga.search_Biz(kw,limit,offset)

if __name__ == '__main__':
    pass

