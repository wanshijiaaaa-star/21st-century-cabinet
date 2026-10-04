# 级联任务分发系统 - 故障排查指南

## 问题1: 级联客户端未初始化

### 症状

运行子节点时出现：
```
级联客户端未初始化
```

### 原因

1. 级联模式未启用
2. 配置不完整（缺少parent_api_url/api_key/api_secret）
3. 配置文件未正确加载

### 解决方案

#### 步骤1: 检查配置

```bash
# 运行测试脚本
python test_cascade_init.py
```

#### 步骤2: 确保config.yaml配置正确

```yaml
# config.yaml
cascade:
  enabled: true
  node_type: child
  parent_api_url: "http://parent-server:8001"
  api_key: "CNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  api_secret: "CSxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  sync_interval: 300
  heartbeat_interval: 60
```

#### 步骤3: 验证初始化

```python
from jobs.cascade_sync import cascade_sync_service

# 手动初始化
cascade_sync_service.initialize()

# 检查是否成功
if cascade_sync_service.client:
    print("✓ 初始化成功")
else:
    print("✗ 初始化失败")
```

### 自动修复

最新版本的 `cascade_task_dispatcher.py` 已添加自动初始化逻辑：

```python
# 如果客户端未初始化，尝试初始化
if not cascade_sync_service.client:
    print_info("级联客户端未初始化，正在初始化...")
    cascade_sync_service.initialize()
```

## 问题2: 无法连接到父节点

### 症状

```
请求父节点失败: 404 - Not Found
请求父节点失败: Connection refused
```

### 原因

1. 父节点地址错误
2. 父节点未启动
3. 网络不通
4. API Key/Secret 错误

### 解决方案

#### 检查父节点状态

```bash
# 测试父节点连接
curl "http://parent-server:8001/api/v1/cascade/heartbeat" \
  -H "Authorization: AK-SK YOUR_API_KEY:YOUR_API_SECRET"
```

#### 验证凭证

```bash
# 在父节点上查看子节点凭证
python jobs/cascade_init.py --list
```

## 问题3: 没有任务可获取

### 症状

```
暂无任务，等待下次轮询...
```

### 原因

1. 父节点没有分配任务
2. 任务已分配给其他节点
3. 任务状态不是pending

### 解决方案

#### 在父节点上手动分发任务

```bash
# 方式1: API调用
curl -X POST "http://localhost:8001/api/v1/cascade/dispatch-task" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# 方式2: 运行示例
python examples/cascade_task_dispatcher_example.py parent
```

#### 检查分配记录

```bash
curl "http://localhost:8001/api/v1/cascade/allocations" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 问题4: 任务执行失败

### 症状

```
处理公众号失败 xxx: ...
执行父节点任务失败: ...
```

### 原因

1. 公众号不存在
2. 网络问题
3. 微信接口限制
4. 配置错误

### 解决方案

#### 检查公众号是否存在

```python
from core.db import DB
from core.models.feed import Feed

session = DB.get_session()
feed = session.query(Feed).filter(Feed.id == "mp_id").first()
if feed:
    print(f"✓ 公众号存在: {feed.mp_name}")
else:
    print("✗ 公众号不存在")
```

#### 检查任务配置

```python
from core.db import DB
from core.models.message_task import MessageTask

session = DB.get_session()
task = session.query(MessageTask).filter(MessageTask.id == "task_id").first()
print(f"任务名称: {task.name}")
print(f"web_hook_url: {task.web_hook_url}")
print(f"mps_id: {task.mps_id}")
```

## 问题5: 模块导入错误

### 症状

```
ModuleNotFoundError: No module named 'core'
```

### 解决方案

已在相关文件中添加路径处理，确保从项目根目录运行：

```bash
# 方式1: 从项目根目录运行
python -m jobs.cascade_task_dispatcher child

# 方式2: 直接运行（已添加路径处理）
cd jobs
python cascade_task_dispatcher.py child
```

## 调试技巧

### 1. 启用详细日志

```python
from core.print import print_info, print_success, print_error, print_warning

print_info("信息日志")
print_success("成功日志")
print_error("错误日志")
print_warning("警告日志")
```

### 2. 检查节点状态

```python
from jobs.cascade_task_dispatcher import cascade_task_dispatcher

# 刷新节点状态
cascade_task_dispatcher.refresh_node_statuses()

# 查看节点状态
for node_id, status in cascade_task_dispatcher.node_statuses.items():
    print(f"节点: {status.node_name}")
    print(f"  在线: {status.is_online}")
    print(f"  可用: {status.is_available}")
    print(f"  容量: {status.current_tasks}/{status.max_capacity}")
```

### 3. 检查分配记录

```python
from jobs.cascade_task_dispatcher import cascade_task_dispatcher

for alloc_id, allocation in cascade_task_dispatcher.allocations.items():
    print(f"分配ID: {alloc_id}")
    print(f"  任务ID: {allocation.task_id}")
    print(f"  公众号数: {len(allocation.feed_ids)}")
    print(f"  状态: {allocation.status}")
```

### 4. 测试API接口

```bash
# 测试获取待处理任务
curl "http://parent:8001/api/v1/cascade/pending-tasks" \
  -H "Authorization: AK-SK CNxxx:CSxxx"

# 测试分发任务
curl -X POST "http://localhost:8001/api/v1/cascade/dispatch-task" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# 测试查看分配
curl "http://localhost:8001/api/v1/cascade/allocations" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 完整测试流程

```bash
# 1. 验证导入
python verify_imports.py

# 2. 测试初始化
python test_cascade_init.py

# 3. 运行完整测试
python test_cascade_task_dispatcher.py

# 4. 父节点分发任务
python examples/cascade_task_dispatcher_example.py parent

# 5. 子节点拉取任务
python examples/cascade_task_dispatcher_example.py child
```

## 常见问题速查表

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 级联客户端未初始化 | 配置不完整 | 检查config.yaml，运行test_cascade_init.py |
| 无法连接父节点 | 地址错误或父节点未启动 | 检查parent_api_url，确保父节点运行 |
| 没有任务 | 未分发任务 | 在父节点运行dispatch-task |
| 任务执行失败 | 公众号不存在或配置错误 | 检查公众号和任务配置 |
| 模块导入错误 | 路径问题 | 从项目根目录运行或使用-m方式 |

## 获取帮助

如果以上方法都无法解决问题：

1. 查看详细日志输出
2. 检查配置文件是否正确加载
3. 确认所有依赖已安装
4. 参考完整文档: `docs/CASCADE_TASK_DISPATCHER.md`
