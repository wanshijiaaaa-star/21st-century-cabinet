# 级联任务分发系统 - 快速参考

## 一分钟快速开始

### 父节点

```bash
# 1. 初始化
python jobs/cascade_init.py --init

# 2. 创建子节点
python jobs/cascade_init.py --child "子节点1" --api-url "http://child:8001"

# 3. 分发任务
curl -X POST "http://localhost:8001/api/v1/cascade/dispatch-task" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 子节点

```bash
# 1. 配置 config.yaml
cascade:
  enabled: true
  node_type: child
  parent_api_url: "http://parent:8001"
  api_key: "CNxxxxxxxx"
  api_secret: "CSxxxxxxxx"

# 2. 测试初始化（可选但推荐）
python test_cascade_init.py

# 3. 启动任务拉取器
# 方式1: 从项目根目录运行
python -m jobs.cascade_task_dispatcher child

# 方式2: 直接运行（已自动添加路径）
cd jobs
python cascade_task_dispatcher.py child
```

## 常用命令

### 分发任务

```bash
# 分发所有任务
curl -X POST "http://localhost:8001/api/v1/cascade/dispatch-task" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# 分发指定任务
curl -X POST "http://localhost:8001/api/v1/cascade/dispatch-task?task_id=xxx" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 查看分配

```bash
# 查看所有分配
curl "http://localhost:8001/api/v1/cascade/allocations" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# 筛选任务
curl "http://localhost:8001/api/v1/cascade/allocations?task_id=xxx&status=executing" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 运行示例

```bash
# 父节点分发示例
python examples/cascade_task_dispatcher_example.py parent

# 子节点拉取示例
python examples/cascade_task_dispatcher_example.py child

# 完整流程示例
python examples/cascade_task_dispatcher_example.py full

# 查看分配情况
python examples/cascade_task_dispatcher_example.py check
```

## API接口速查

| 接口 | 方法 | 认证 | 用途 |
|------|------|------|------|
| /cascade/dispatch-task | POST | JWT | 触发任务分发 |
| /cascade/pending-tasks | GET | AK-SK | 获取待处理任务 |
| /cascade/allocations | GET | JWT | 查看分配记录 |

## 配置模板

### 父节点 config.yaml

```yaml
cascade:
  enabled: true
  node_type: parent
```

### 子节点 config.yaml

```yaml
cascade:
  enabled: true
  node_type: child
  parent_api_url: "http://parent-server:8001"
  api_key: "CNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  api_secret: "CSxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  sync_interval: 300
  heartbeat_interval: 60
```

## 节点配置

### 设置节点容量

```bash
curl -X PUT "http://localhost:8001/api/v1/cascade/nodes/NODE_ID" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sync_config": {
      "max_capacity": 20,
      "feed_quota": {
        "mp_id_1": 5,
        "mp_id_2": 10
      }
    }
  }'
```

## 状态说明

### 节点状态

- `is_active`: 节点是否启用
- `status`: 0=离线, 1=在线
- `current_tasks`: 当前任务数
- `max_capacity`: 最大容量

### 分配状态

- `pending`: 已分配，待执行
- `executing`: 正在执行
- `completed`: 执行完成
- `failed`: 执行失败

## 故障排查

### 子节点无法获取任务

```bash
# 1. 检查配置
python jobs/cascade_init.py --check

# 2. 查看节点状态
python jobs/cascade_init.py --list

# 3. 查看分配记录
curl "http://localhost:8001/api/v1/cascade/allocations"
```

### 节点显示离线

```bash
# 检查心跳是否正常
# 超过3分钟无心跳视为离线

# 手动测试连接
curl -X POST "http://localhost:8001/api/v1/cascade/nodes/NODE_ID/test-connection" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 核心概念

### 负载均衡

- 根据节点可用容量选择
- 支持配额优先分配
- 避免单点过载

### 任务分配流程

```
1. 父节点获取所有在线节点
2. 解析任务关联的公众号
3. 为每个公众号选择节点
4. 创建任务分配记录
5. 推送到子节点
6. 子节点拉取并执行
7. 上报执行结果
```

## 文件位置

- **分发器**: `jobs/cascade_task_dispatcher.py`
- **API接口**: `apis/cascade.py`
- **示例**: `examples/cascade_task_dispatcher_example.py`
- **测试**: `test_cascade_task_dispatcher.py`
- **文档**: `docs/CASCADE_TASK_DISPATCHER.md`

## 测试

```bash
# 运行所有测试
python test_cascade_task_dispatcher.py
```

## 相关文档

- [详细指南](CASCADE_TASK_DISPATCHER.md)
- [实现总结](CASCADE_TASK_DISPATCHER_SUMMARY.md)
- [级联系统](CASCADE_README.md)
