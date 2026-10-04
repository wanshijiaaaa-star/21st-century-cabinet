"""诊断级联配置问题"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import cfg

print("="*60)
print("诊断级联配置")
print("="*60)
print()

# 获取配置
cascade_config = cfg.get("cascade", {})

print("原始配置值:")
print(f"  enabled: {repr(cascade_config.get('enabled'))}")
print(f"  node_type: {repr(cascade_config.get('node_type'))}")
print(f"  parent_api_url: {repr(cascade_config.get('parent_api_url'))}")
print(f"  api_key: {repr(cascade_config.get('api_key'))}")
print(f"  api_secret: {repr(cascade_config.get('api_secret'))}")
print()

# 检查parent_api_url
parent_url = cascade_config.get('parent_api_url')

if parent_url:
    print(f"parent_api_url 详细信息:")
    print(f"  类型: {type(parent_url)}")
    print(f"  长度: {len(parent_url)}")
    print(f"  值: '{parent_url}'")
    print(f"  是否以http://开头: {parent_url.startswith('http://')}")
    print(f"  是否以https://开头: {parent_url.startswith('https://')}")
    print(f"  前20个字符: '{parent_url[:20]}'")
    print(f"  repr: {repr(parent_url)}")
    print()

    # 问题诊断
    if not parent_url.startswith(('http://', 'https://')):
        print("❌ 问题: URL缺少协议前缀!")
        print()

        # 可能的原因
        if parent_url.startswith('"'):
            print("原因: 配置值包含了多余的引号")
            print(f"  当前值: {parent_url}")
            print(f"  应该是: {parent_url.strip('\"')}")
        else:
            print("原因: URL格式不正确")
            print("应该是: http://localhost:8001 或 https://your-server.com")
    else:
        print("✓ URL格式正确")
else:
    print("❌ parent_api_url 为空或未配置")

print()
print("="*60)
print("环境变量检查")
print("="*60)
print()

import os
env_vars = [
    'CASCADE_ENABLED',
    'CASCADE_NODE_TYPE',
    'CASCADE_PARENT_API_URL',
    'CASCADE_API_KEY',
    'CASCADE_API_SECRET'
]

for var in env_vars:
    value = os.environ.get(var)
    if value:
        print(f"{var}: '{value}'")
    else:
        print(f"{var}: (未设置)")
