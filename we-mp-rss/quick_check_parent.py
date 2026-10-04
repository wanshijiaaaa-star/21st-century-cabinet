"""快速检查父节点状态"""

import subprocess
import sys

print("="*60)
print("父节点状态快速检查")
print("="*60)
print()

# 检查1: 确认服务是否运行
print("检查1: 父节点服务状态")
print("-" * 60)
try:
    result = subprocess.run(
        ["netstat", "-ano"],
        capture_output=True,
        text=True,
        timeout=5
    )

    # 检查8001端口
    lines = result.stdout.split('\n')
    port_8001_found = False
    for line in lines:
        if ':8001' in line and 'LISTENING' in line:
            port_8001_found = True
            print(f"✓ 端口8001正在监听")
            print(f"  {line.strip()}")
            break

    if not port_8001_found:
        print("✗ 端口8001未监听")
        print("  请启动父节点服务: python main.py")

except Exception as e:
    print(f"✗ 无法检查端口: {str(e)}")
    print("  请手动检查父节点服务是否运行")

print()

# 检查2: 使用curl测试接口
print("检查2: 测试API接口")
print("-" * 60)
print("运行以下命令测试心跳接口:")
print()
print('curl -X POST "http://localhost:8001/api/v1/cascade/heartbeat" \\')
print('  -H "Authorization: AK-SK CNtest:CStest" \\')
print('  -H "Content-Type: application/json"')
print()
print("预期结果:")
print("  - 如果返回 401: 认证失败（正常，凭证错误）")
print("  - 如果返回 405: 方法不允许（问题）")
print("  - 如果返回 404: 接口不存在（父节点未启动或路由问题）")
print("  - 如果连接失败: 父节点未运行")
print()

# 检查3: 查看API文档
print("检查3: API文档访问")
print("-" * 60)
print("在浏览器中打开:")
print("  http://localhost:8001/api/docs")
print()
print("查找以下接口:")
print("  - POST /api/v1/cascade/heartbeat")
print("  - GET  /api/v1/cascade/feeds")
print("  - GET  /api/v1/cascade/message-tasks")
print()
print("如果找不到这些接口，说明:")
print("  1. apis/cascade.py 文件不存在")
print("  2. 路由未正确注册")
print("  3. 需要重启父节点服务")
print()

# 检查4: 文件检查
print("检查4: 关键文件检查")
print("-" * 60)

import os

files_to_check = [
    ("apis/cascade.py", "级联API接口"),
    ("core/cascade.py", "级联核心模块"),
    ("core/auth.py", "认证模块"),
]

for file_path, desc in files_to_check:
    full_path = os.path.join(os.path.dirname(__file__), file_path)
    if os.path.exists(full_path):
        print(f"✓ {desc}: {file_path}")
    else:
        print(f"✗ {desc}缺失: {file_path}")

print()

# 检查5: 路由注册检查
print("检查5: 路由注册检查")
print("-" * 60)

web_py_path = os.path.join(os.path.dirname(__file__), "web.py")
if os.path.exists(web_py_path):
    with open(web_py_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'cascade_router' in content:
        print("✓ cascade_router 已导入")

        if 'include_router(cascade_router)' in content:
            print("✓ cascade_router 已注册")
        else:
            print("✗ cascade_router 未注册到api_router")
            print("  请在 web.py 中添加: api_router.include_router(cascade_router)")
    else:
        print("✗ cascade_router 未导入")
        print("  请在 web.py 中添加: from apis.cascade import router as cascade_router")
else:
    print("✗ web.py 文件不存在")

print()
print("="*60)
print("解决方案")
print("="*60)
print()

print("如果端口8001未监听:")
print("  1. 确保在项目根目录下运行")
print("  2. 运行: python main.py")
print("  3. 或运行: python -m uvicorn web:app --host 0.0.0.0 --port 8001")
print()

print("如果接口返回404:")
print("  1. 检查 apis/cascade.py 文件是否存在")
print("  2. 检查 web.py 中是否注册了 cascade_router")
print("  3. 重启父节点服务")
print()

print("如果接口返回405:")
print("  1. 检查HTTP方法是否正确（心跳接口是POST）")
print("  2. 检查URL路径是否正确")
print("  3. 查看API文档确认接口定义")
print()

print("如果连接失败:")
print("  1. 确认父节点服务已启动")
print("  2. 检查防火墙设置")
print("  3. 尝试 ping localhost")
