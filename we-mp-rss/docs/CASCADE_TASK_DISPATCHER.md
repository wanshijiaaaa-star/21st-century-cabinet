# 级联任务分发系统使用指南

## 概述

级联任务分发系统是WeRSS的核心功能之一，用于在父子节点之间智能分配和执行公众号更新任务。

### 核心特性

- **智能负载均衡**: 根据节点空闲情况自动分配公众号任务
- **灵活配额配置**: 支持为特定节点配置公众号处理配额
- **实时状态监控**: 监控子节点在线状态和任务执行情况
- **任务结果上报**: 子节点执行完成后自动上报结果到父节点
- **容错机制**: 节点离线或任务失败时自动重试或重新分配

### 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                      父节点 (Parent)                    │
│  ┌─────────────────────────────────────────────────┐   │
│  │         CascadeTaskDispatcher (分发器)           │   │
│  │  • 刷新节点状态                                    │   │
│  │  • 智能选择节点                                    │   │
│  │  • 分配公众号任务                                  │   │
│  │  • 推送任务到子节点                                │   │
│  └─────────────────────────────────────────────────┘   │
│                         │                               │
│                         ▼                               │
│                   HTTP API 接口                          │
│  • POST /api/v1/cascade/dispatch-task                   │
│  • GET  /api/v1/cascade/pending-tasks                   │
│  • GET  /api/v1/cascade/allocations                     │
└─────────────────────────────────────────────────────────┘
                         │
                         │ AK-SK 认证
                         │
┌────────────────────────┼────────────────────────────────┐
│                        ▼                                 │
│              子节点1 (Child1)     子节点2 (Child2)       │
│  ┌──────────────────────┐  ┌──────────────────────┐    │
│  │  任务拉取器           │  │  任务拉取器           │    │
│  │  • 定期拉取任务       │  │  • 定期拉取任务       │    │
│  │  • 执行公众号更新     │  │  • 执行公众号更新     │    │
│  │  • 上报执行结果       │  │  • 上报执行结果       │    │
│  └──────────────────────┘  └──────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 配置父节点

父节点不需要特殊配置，只需确保：

1. 启用了级联模式
2. 已创建子节点记录
3. 子节点已生成并配置了AK/SK凭证

在 `config.yaml` 中配置：

```yaml
cascade:
  enabled: true
  node_type: parent
```

### 2. 配置子节点

在 `config.yaml` 中配置子节点：

```yaml
cascade:
  enabled: true
  node_type: child
  parent_api_url: http://parent-server:8001
  api_key: CNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  api_secret: CSxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  sync_interval: 300        # 同步间隔（秒）
  heartbeat_interval: 60    # 心跳间隔（秒）
```

### 3. 初始化级联系统

```bash
# 父节点：初始化数据库
python jobs/cascade_init.py --init

# 父节点：创建子节点记录
python jobs/cascade_init.py --child "子节点1" --desc "用于扩展采集" --api-url "http://child-node1:8001"

# 父节点：生成子节点凭证
python jobs/cascade_init.py --list
```

生成的凭证会显示在控制台，请妥善保存并配置到子节点。

### 4. 分发任务

#### 方式1: 通过API手动分发

```bash
# 分发所有任务
curl -X POST "http://localhost:8001/api/v1/cascade/dispatch-task" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# 分发指定任务
curl -X POST "http://localhost:8001/api/v1/cascade/dispatch-task?task_id=xxx" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### 方式2: 通过脚本分发

```bash
# 运行分发示例
python examples/cascade_task_dispatcher_example.py parent
```

#### 方式3: 通过程序代码分发

```python
from jobs.cascade_task_dispatcher import cascade_task_dispatcher
import asyncio

async def dispatch():
    # 刷新节点状态
    cascade_task_dispatcher.refresh_node_statuses()
    
    # 分发所有任务
    await cascade_task_dispatcher.execute_dispatch()
    
    # 分发指定任务
    await cascade_task_dispatcher.execute_dispatch(task_id="xxx")

asyncio.run(dispatch())
```

### 5. 启动子节点任务拉取器

```bash
# 运行子节点任务拉取示例
python examples/cascade_task_dispatcher_example.py child

# 或直接运行
python jobs/cascade_task_dispatcher.py child
```

子节点会定期从父节点拉取待处理任务并执行。

## 节点配置详解

### 节点容量配置

可以通过节点的 `sync_config` 字段配置节点容量：

```python
# 通过API更新节点配置
import requests

node_config = {
    "max_capacity": 20,  # 最大并发任务数
    "feed_quota": {      # 公众号配额（可选）
        "mp_id_1": 5,
        "mp_id_2": 10
    }
}

response = requests.put(
    "http://localhost:8001/api/v1/cascade/nodes/NODE_ID",
    json={"sync_config": node_config},
    headers={"Authorization": "Bearer YOUR_JWT_TOKEN"}
)
```

配置说明：

- `max_capacity`: 节点最大并发任务数，默认10
- `feed_quota`: 公众号配额字典，指定哪些公众号优先由该节点处理

### 节点状态说明

节点状态由以下因素决定：

1. **is_active**: 节点是否启用（管理员控制）
2. **status**: 节点状态（0=离线, 1=在线）
3. **last_heartbeat**: 最后心跳时间（超过3分钟视为离线）
4. **current_tasks**: 当前执行的任务数
5. **max_capacity**: 最大容量

节点可用性判断：
```python
is_available = is_active and status == 1 and (now - last_heartbeat) < 180s and current_tasks < max_capacity
```

## API 接口文档

### 父节点接口

#### 1. 手动触发任务分发

```http
POST /api/v1/cascade/dispatch-task
Authorization: Bearer <JWT_TOKEN>

Query Parameters:
  - task_id (可选): 指定任务ID，不指定则分发所有任务

Response:
{
  "code": 200,
  "message": "任务分发完成",
  "data": null
}
```

#### 2. 查看任务分配情况

```http
GET /api/v1/cascade/allocations
Authorization: Bearer <JWT_TOKEN>

Query Parameters:
  - task_id (可选): 按任务ID筛选
  - node_id (可选): 按节点ID筛选
  - status (可选): 按状态筛选 (pending, executing, completed, failed)
  - limit: 每页数量（默认50）

Response:
{
  "code": 200,
  "data": {
    "list": [
      {
        "allocation_id": "xxx",
        "node_id": "xxx",
        "node_name": "子节点1",
        "task_id": "xxx",
        "feed_ids": ["mp1", "mp2"],
        "status": "executing",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
      }
    ],
    "total": 10
  }
}
```

### 子节点接口

#### 1. 获取待处理任务

```http
GET /api/v1/cascade/pending-tasks
Authorization: AK-SK <API_KEY>:<API_SECRET>

Query Parameters:
  - limit: 获取任务数量限制（默认1）

Response:
{
  "code": 200,
  "data": {
    "task_id": "xxx",
    "task_name": "任务名称",
    "message_type": 0,
    "message_template": "...",
    "web_hook_url": "https://...",
    "cron_exp": "0 9 * * *",
    "headers": "",
    "cookies": "",
    "feeds": [
      {
        "id": "mp1",
        "faker_id": "fake1",
        "mp_name": "公众号1",
        "mp_cover": "https://...",
        "mp_intro": "公众号简介",
        "status": 1
      }
    ],
    "dispatched_at": "2024-01-01T00:00:00",
    "allocation_id": "xxx"
  }
}
```

## 使用场景

### 场景1: 大规模公众号采集

当需要采集大量公众号时，可以使用多个子节点分担负载：

1. 父节点配置1000个公众号
2. 创建5个子节点，每个节点最大容量20
3. 父节点自动将公众号分配给不同子节点
4. 子节点并行处理，大幅提升采集速度

### 场景2: 地理分布采集

不同地区的节点可以访问本地微信公众号接口：

1. 节点A（北京）：配置 `feed_quota = {"beijing_mp": 100}`
2. 节点B（上海）：配置 `feed_quota = {"shanghai_mp": 100}`
3. 父节点根据配额优先分配对应地区的公众号

### 场景3: 高可用保障

配置多个子节点作为备份：

1. 主节点故障时，任务自动重新分配
2. 节点上线后自动加入负载均衡
3. 任务执行失败自动重试

## 监控和调试

### 查看节点状态

```bash
# 列出所有节点
python jobs/cascade_init.py --list

# 查看分配情况
python examples/cascade_task_dispatcher_example.py check
```

### 查看同步日志

```bash
# 通过API查询
curl "http://localhost:8001/api/v1/cascade/sync-logs?limit=50" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 测试节点连接

```bash
# 通过API测试连接
curl -X POST "http://localhost:8001/api/v1/cascade/nodes/NODE_ID/test-connection" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"api_url": "http://child:8001", "api_key": "CNxxx", "api_secret": "CSxxx"}'
```

## 故障排除

### 问题1: 子节点无法获取任务

**可能原因**:
- 子节点AK/SK配置错误
- 子节点未在线（检查心跳）
- 父节点没有分配任务

**解决方法**:
```bash
# 检查配置
python jobs/cascade_init.py --check

# 检查节点状态
python jobs/cascade_init.py --list

# 查看分配记录
curl "http://localhost:8001/api/v1/cascade/allocations" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 问题2: 任务分配不均

**可能原因**:
- 节点容量配置不合理
- 节点配额配置导致分配偏差

**解决方法**:
- 调整节点的 `max_capacity`
- 检查并调整 `feed_quota`
- 刷新节点状态：`cascade_task_dispatcher.refresh_node_statuses()`

### 问题3: 任务执行失败

**可能原因**:
- 子节点网络问题
- 微信公众号接口限制
- 配置错误（headers, cookies）

**解决方法**:
- 查看子节点日志
- 检查微信公众号接口状态
- 验证task配置

## 最佳实践

1. **节点容量规划**: 根据服务器性能合理设置 `max_capacity`
2. **配额使用**: 对重要的公众号设置特定节点配额
3. **监控告警**: 定期检查节点在线状态和任务执行情况
4. **负载均衡**: 保持各节点负载均衡，避免单点过载
5. **容错设计**: 配置多个子节点作为备份

## 相关文档

- [级联系统总览](CASCADE_README.md)
- [级联系统快速开始](CASCADE_QUICKSTART.md)
- [级联系统完整指南](CASCADE_GUIDE.md)
- [AK认证系统](AK_Authentication_Guide.md)
