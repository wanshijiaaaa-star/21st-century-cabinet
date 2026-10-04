import requests
from core.ver import *
try:
    response = requests.get('https://api.github.com/repos/rachelos/we-mp-rss/releases/latest')
    response.raise_for_status()  # 检查请求是否成功
    data = response.json()
    LATEST_VERSION = data.get('tag_name', '').replace('v', '')
except requests.RequestException as e:
    print(f"Failed to fetch latest version: {e}")
    LATEST_VERSION = ''
except ValueError as e:
    print(f"Failed to parse JSON response: {e}")
    LATEST_VERSION = ''

#API接口前缀
API_BASE = "/api/v1/wx"

#工作目录
WORK_DIR="./work"

#静态文件目录
STATIC_DIR="./static"