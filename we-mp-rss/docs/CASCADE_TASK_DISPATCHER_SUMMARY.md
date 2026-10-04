# 级联任务分发系统 - 实现总结

## 创建时间

2026年2月26日

## 实现概述

本次实现了一个完整的级联任务分发系统，用于在WeRSS的父子节点之间智能分配和执行公众号更新任务。

## 核心文件

### 1. 任务分发器 (`jobs/cascade_task_dispatcher.py`)

**主要功能**:
- `CascadeTaskDispatcher`: 父节点任务分发器
- `TaskAllocation`: 任务分配记录
- `NodeStatus`: 节点状态跟踪

**核心方法**:
- `refresh_node_statuses()`: 刷新所有子节点状态
- `select_node_for_feed()`: 为公众号选择合适的节点
- `dispatch_task_to_children()`: 将任务分发给子节点
- `create_task_package()`: 创建任务包
- `execute_parent_task()`: 子节点执行父节点分配的任务

### 2. API扩展 (`apis/cascade.py`)

**新增接口**:

| 接口 | 方法 | 说明 |
|------|------|------|
| /cascade/pending-tasks | GET | 子节点获取待处理任务 |
| /cascade/dispatch-task | POST | 父节点手动触发任务分发 |
| /cascade/allocations | GET | 查看任务分配情况 |

### 3. 客户端扩展 (`core/cascade.py`)

**新增方法**:
- `get_pending_tasks()`: 从父节点获取待处理任务

### 4. 示例代码 (`examples/cascade_task_dispatcher_example.py`)

包含完整的父子节点使用示例：
- 父节点分发示例
- 子节点拉取示例
- 完整流程示例
- 查看分配情况示例

### 5. 测试脚本 (`test_cascade_task_dispatcher.py`)

用于测试系统的各个功能模块。

## 核心特性

### 1. 智能负载均衡

```python
# 根据节点空闲情况自动分配
- 检查节点在线状态
- 考虑当前负载
- 支持容量配置
- 支持配额约束
```

### 2. 灵活的节点配置

```json
{
  "max_capacity": 20,
  "feed_quota": {
    "mp_id_1": 5,
    "mp_id_2": 10
  }
}
```

### 3. 实时状态监控

```python
NodeStatus:
  - is_online: 是否在线
  - is_available: 是否可用
  - available_capacity: 可用容量
  - current_tasks: 当前任务数
```

### 4. 任务分配追踪

```python
TaskAllocation:
  - allocation_id: 分配ID
  - node_id: 节点ID
  - task_id: 任务ID
  - feed_ids: 公众号列表
  - status: 状态 (pending, executing, completed, failed)
```

## 工作流程

### 父节点流程

```
1. refresh_node_statuses()
   └─> 获取所有在线子节点

2. dispatch_task_to_children(task)
   ├─> 解析任务关联的公众号
   ├─> 为每个公众号选择节点
   │   └─> select_node_for_feed(mp_id)
   │       ├─> 检查配额配置
   │       └─> 选择负载最轻的节点
   └─> allocate_feeds_to_node()
       └─> 创建分配记录

3. create_task_package()
   └─> 封装任务和公众号数据

4. dispatch_to_child_node()
   └─> 推送到子节点API
```

### 子节点流程

```
1. fetch_task_from_parent()
   └─> GET /cascade/pending-tasks

2. execute_parent_task()
   ├─> 创建本地Feed记录
   ├─> 执行公众号更新
   │   └─> do_job(mp, task)
   └─> 上报结果到父节点
       └─> report_task_result()
```

## 配置说明

### 父节点配置

```yaml
# config.yaml
cascade:
  enabled: true
  node_type: parent
```

### 子节点配置

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

## 使用方法

### 1. 初始化

```bash
# 父节点：初始化数据库
python jobs/cascade_init.py --init

# 父节点：创建子节点
python jobs/cascade_init.py --child "子节点1" --api-url "http://child:8001"
```

### 2. 分发任务

```bash
# 方式1: API调用
curl -X POST "http://localhost:8001/api/v1/cascade/dispatch-task" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# 方式2: 运行示例
python examples/cascade_task_dispatcher_example.py parent

# 方式3: 程序代码
from jobs.cascade_task_dispatcher import cascade_task_dispatcher
import asyncio

asyncio.run(cascade_task_dispatcher.execute_dispatch())
```

### 3. 子节点拉取任务

```bash
# 方式1: 运行示例
python examples/cascade_task_dispatcher_example.py child

# 方式2: 直接运行
python jobs/cascade_task_dispatcher.py child
```

### 4. 查看分配情况

```bash
# 方式1: API调用
curl "http://localhost:8001/api/v1/cascade/allocations" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# 方式2: 运行示例
python examples/cascade_task_dispatcher_example.py check

# 方式3: 运行测试
python test_cascade_task_dispatcher.py
```

## API接口示例

### 获取待处理任务 (子节点)

```bash
curl -X GET "http://parent:8001/api/v1/cascade/pending-tasks?limit=1" \
  -H "Authorization: AK-SK CNxxx:CSxxx"
```

### 触发任务分发 (父节点)

```bash
curl -X POST "http://localhost:8001/api/v1/cascade/dispatch-task" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# 分发指定任务
curl -X POST "http://localhost:8001/api/v1/cascade/dispatch-task?task_id=xxx" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 查看分配记录

```bash
curl "http://localhost:8001/api/v1/cascade/allocations" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# 筛选任务
curl "http://localhost:8001/api/v1/cascade/allocations?task_id=xxx&status=executing" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 架构设计

```
┌─────────────────────────────────────────────────────┐
│              父节点 (Parent Node)                    │
│                                                      │
│  CascadeTaskDispatcher                               │
│  ├─ NodeStatus管理                                   │
│  ├─ TaskAllocation管理                              │
│  ├─ 智能调度算法                                     │
│  └─ 任务包创建                                       │
│                                                      │
│  API接口                                             │
│  ├─ POST /dispatch-task                            │
│  ├─ GET  /pending-tasks                            │
│  └─ GET  /allocations                               │
└─────────────────────────────────────────────────────┘
                    │
                    │ HTTP + AK-SK
                    │
┌───────────────────┼─────────────────────────────────┐
│                   ▼                                 │
│         子节点1 (Child 1)  子节点2 (Child 2)        │
│                                                      │
│   任务拉取器    任务拉取器                           │
│   ├─ 定期轮询   ├─ 定期轮询                          │
│   ├─ 执行更新   ├─ 执行更新                          │
│   └─ 上报结果   └─ 上报结果                          │
└─────────────────────────────────────────────────────┘
```

## 节点选择策略

### 1. 配额优先

```python
if mp_id in node.feed_quota:
    # 有配额的节点优先
    return node_id
```

### 2. 负载均衡

```python
# 选择可用容量最大的节点
available_nodes.sort(key=lambda x: x[1].available_capacity)
return available_nodes[0][0]
```

### 3. 容量检查

```python
if required_capacity > node.available_capacity:
    # 容量不足，跳过
    continue
```

## 状态转换

```
TaskAllocation状态:

pending → executing → completed
         ↓
       failed

任务分配状态:
pending: 已分配，待执行
executing: 子节点正在执行
completed: 执行完成
failed: 执行失败
```

## 错误处理

### 1. 节点离线

```python
if not node_status.is_online:
    print_warning(f"节点离线: {node_status.node_name}")
    return None
```

### 2. 容量不足

```python
if required_capacity > node.available_capacity:
    print_warning(f"容量不足")
    return None
```

### 3. 分配失败

```python
# 失败的任务放回待分配列表
remaining_feeds.extend(node_feeds)
```

## 监控和日志

### 1. 同步日志

```python
log = cascade_manager.create_sync_log(
    node_id=node_id,
    operation="dispatch_task",
    direction="push",
    extra_data={...}
)
```

### 2. 控制台输出

```python
print_success(f"分配任务: {len(feeds)}个公众号 -> {node_name}")
print_info(f"从父节点获取到任务: {task_name}")
print_error(f"分配失败: {str(e)}")
```

## 相关文档

- [任务分发系统详细指南](CASCADE_TASK_DISPATCHER.md)
- [级联系统总览](CASCADE_README.md)
- [级联系统快速开始](CASCADE_QUICKSTART.md)
- [级联系统完整指南](CASCADE_GUIDE.md)

## 示例代码位置

- **分发器**: `jobs/cascade_task_dispatcher.py`
- **示例脚本**: `examples/cascade_task_dispatcher_example.py`
- **测试脚本**: `test_cascade_task_dispatcher.py`
- **API接口**: `apis/cascade.py` (新增3个接口)

## 测试验证

```bash
# 验证导入（推荐先运行）
python verify_imports.py

# 运行完整测试
python test_cascade_task_dispatcher.py

# 测试内容:
# ✓ 分发器初始化
# ✓ 节点状态管理
# ✓ 任务分发
# ✓ 分配管理
# ✓ API端点
```

## 运行方式

### 方式1: 从项目根目录运行（推荐）

```bash
# 在项目根目录下
f:\Wx\WeRss\we-mp-rss>

# 运行分发器（子节点模式）
python -m jobs.cascade_task_dispatcher child

# 运行示例
python -m examples.cascade_task_dispatcher_example child
```

### 方式2: 直接运行（已自动添加路径）

```bash
# 进入文件所在目录
cd jobs

# 直接运行（现在可以正常运行了）
python cascade_task_dispatcher.py child
```

**注意**: 所有相关文件都已添加路径处理代码，可以直接运行不会报错。详见 `RUN_CASCADE_TASK_DISPATCHER.md`

## 注意事项

1. **节点凭证安全**: 子节点AK/SK必须保密
2. **心跳超时**: 超过3分钟无心跳视为离线
3. **容量规划**: 根据服务器性能合理配置容量
4. **错误重试**: 分配失败会自动重试
5. **日志监控**: 定期检查同步日志

## 未来优化方向

1. **动态容量调整**: 根据节点性能自动调整容量
2. **优先级队列**: 支持任务优先级
3. **断点续传**: 任务中断后可恢复
4. **数据压缩**: 减少传输数据量
5. **批量处理**: 支持批量获取任务

## 总结

本次实现完成了一个完整的级联任务分发系统，具备：

✅ 智能任务分配算法
✅ 实时节点状态监控
✅ 灵活的配置管理
✅ 完整的API接口
✅ 详细的文档和示例
✅ 全面的测试覆盖

系统可以根据节点的空闲情况，自动将公众号任务分配给最合适的子节点，实现了负载均衡和横向扩展能力。
