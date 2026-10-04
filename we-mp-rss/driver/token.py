__package__ = "driver"
from core.config import Config,cfg
# 确保data目录和wx.lic文件存在
import os
import json
from core.print import print_success, print_warning
from core.redis_client import redis_client

REDIS_TOKEN_PREFIX = "werss:token:"

lic_path="./data/wx.lic"
os.makedirs(os.path.dirname(lic_path), exist_ok=True)
if not os.path.exists(lic_path):
    with open(lic_path, "w") as f:
        f.write("{}")
wx_cfg = Config(lic_path)

def set_token(data:any,ext_data:any=None):

    """
    设置微信登录的Token和Cookie信息
    :param data: 包含Token和Cookie信息的字典
    """
    if data.get("token", "") == "":
        return

    token_data = {
        "token": data.get("token", ""),
        "cookie": data.get("cookies_str", ""),
        "fingerprint": data.get("fingerprint", ""),
        "expiry": data.get("expiry", {}),
    }
    if ext_data is not None:
        token_data["ext_data"] = ext_data

    # 优先存储到Redis，整体存储
    if redis_client.is_connected:
        try:
            _save_to_local(token_data)
            redis_client._client.set(REDIS_TOKEN_PREFIX + "data", json.dumps(token_data))
            print_success("Token已存储到Redis")
        except Exception as e:
            print_warning(f"Redis存储失败，回退到本地文件: {e}")
    else:
        _save_to_local(token_data)

    print_success(f"Token:{data.get('token')} \n到期时间:{data.get('expiry')['expiry_time']}\n")
    from jobs.notice import sys_notice

#     sys_notice(f"""WeRss授权成功
# - Token: {data.get("token")}
# - Expiry: {data.get("expiry")['expiry_time']}
# """, str(cfg.get("server.code_title","WeRss授权成功")))


def _save_to_local(token_data: dict):
    """保存到本地文件"""
    # 先重新加载文件最新内容，避免 wx_cfg 单例用启动时的陈旧内存
    # 整文件覆盖其他模块写入的数据（如 weread_data）
    wx_cfg.reload()
    wx_cfg.set("token_data", token_data)
    wx_cfg.save_config()
    wx_cfg.reload()


def get(key:str,default:str="")->str:
    """从整体token_data中获取指定字段"""
    token_data = _get_token_data()
    if token_data is None:
        return default
    value = token_data.get(key, default)
    if isinstance(value, dict):
        return json.dumps(value)
    if value=="None":
        return ''
    return str(value) if value is not None else default


def _get_token_data() -> dict | None:
    """获取整体token_data"""
    # 优先从Redis获取
    if redis_client.is_connected:
        try:
            value = redis_client._client.get(REDIS_TOKEN_PREFIX + "data")
            if value is not None:
                return json.loads(value)
        except Exception as e:
            print_warning(f"Redis读取失败，回退到本地文件: {e}")
    # 回退到本地文件
    return wx_cfg.get("token_data", None)