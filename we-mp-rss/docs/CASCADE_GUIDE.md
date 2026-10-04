# WeRSS 级联系统使用指南

## 概述

WeRSS 级联系统支持父子节点架构，允许您：
- 在父节点统一管理公众号数据和消息任务
- 子节点从父节点同步数据并执行任务
- 子节点将执行结果上报回父节点

## 架构说明

### 父节点
- 存储主数据库（公众号、消息任务、文章等）
- 提供API接口供子节点拉取数据
- 接收子节点上报的任务执行结果
- 管理子节点和同步日志

### 子节点
- 从父节点拉取公众号和消息任务数据
- 执行消息任务（采集、推送等）
- 将执行结果上报到父节点
- 支持独立部署，扩展采集能力

## 配置步骤

### 1. 父节点配置

父节点无需特殊配置，默认为独立模式运行。需要通过API管理子节点。

```yaml
# config.yaml
cascade:
  enabled: False  # 父节点不需要启用级联
  node_type: parent
```

### 2. 子节点配置

子节点需要配置父节点连接信息：

```yaml
# config.yaml
cascade:
  enabled: True
  node_type: child
  parent_api_url: "http://parent-server:8001"  # 父节点API地址
  api_key: "CNxxxxx"  # 从父节点获取的API Key
  api_secret: "CSxxxxx"  # 从父节点获取的Secret
  sync_interval: 300  # 同步间隔（秒）
  heartbeat_interval: 60  # 心跳间隔（秒）
```

### 3. 环境变量配置

也可以通过环境变量配置：

```bash
# 父节点（默认）
CASCADE_ENABLED=False

# 子节点
CASCADE_ENABLED=True
CASCADE_NODE_TYPE=child
CASCADE_PARENT_URL=http://parent-server:8001
CASCADE_API_KEY=CNxxxxx
CASCADE_API_SECRET=CSxxxxx
CASCADE_SYNC_INTERVAL=300
CASCADE_HEARTBEAT_INTERVAL=60
```

## API使用指南

### 父节点管理接口

#### 1. 创建子节点

```bash
POST /api/v1/cascade/nodes
Content-Type: application/json
Authorization: Bearer {token}

{
  "node_type": 1,
  "name": "子节点1",
  "description": "用于扩展采集能力",
  "api_url": "http://child-server:8001"
}
```

响应：
```json
{
  "code": 0,
  "message": "节点创建成功",
  "data": {
    "node_id": "550e8400-e29b-41d4-a716-446655440000",
    "node_type": 1,
    "name": "子节点1",
    "is_active": true
  }
}
```

#### 2. 生成子节点凭证

```bash
POST /api/v1/cascade/nodes/{node_id}/credentials
Authorization: Bearer {token}
```

响应（**请妥善保存，仅显示一次**）：
```json
{
  "code": 0,
  "message": "凭证生成成功",
  "data": {
    "node_id": "550e8400-e29b-41d4-a716-446655440000",
    "api_key": "CN32个随机字符",
    "api_secret": "CS32个随机字符"
  }
}
```

#### 3. 获取节点列表

```bash
GET /api/v1/cascade/nodes?node_type=1
Authorization: Bearer {token}
```

#### 4. 测试节点连接

```bash
POST /api/v1/cascade/nodes/{node_id}/test-connection
Authorization: Bearer {token}

{
  "api_url": "http://child-server:8001",
  "api_key": "CNxxxxx",
  "api_secret": "CSxxxxx"
}
```

#### 5. 查看同步日志

```bash
GET /api/v1/cascade/sync-logs?node_id={node_id}&limit=50
Authorization: Bearer {token}
```

### 子节点调用接口（由系统自动使用）

子节点通过 `CascadeClient` 自动调用以下接口：

#### 从父节点拉取公众号
```bash
GET /api/v1/cascade/feeds
Authorization: AK-SK {api_key}:{api_secret}
```

#### 从父节点拉取消息任务
```bash
GET /api/v1/cascade/message-tasks
Authorization: AK-SK {api_key}:{api_secret}
```

#### 上报任务结果
```bash
POST /api/v1/cascade/report-result
Authorization: AK-SK {api_key}:{api_secret}

{
  "task_id": "task-uuid",
  "results": [
    {
      "mp_id": "mp-uuid",
      "mp_name": "公众号名称",
      "article_count": 10,
      "success_count": 10,
      "timestamp": "2024-01-01T00:00:00"
    }
  ],
  "timestamp": "2024-01-01T00:00:00"
}
```

#### 发送心跳
```bash
POST /api/v1/cascade/heartbeat
Authorization: AK-SK {api_key}:{api_secret}
```

## 工作流程

### 1. 初始化流程

**父节点：**
1. 启动父节点服务
2. 登录管理后台
3. 创建子节点并生成凭证
4. 将凭证提供给子节点管理员

**子节点：**
1. 配置 `config.yaml` 中的级联参数
2. 启动子节点服务
3. 系统自动连接父节点并开始同步

### 2. 数据同步流程

```
子节点启动
    ↓
发送心跳到父节点
    ↓
拉取公众号数据
    ↓
拉取消息任务
    ↓
定时任务执行（采集、推送）
    ↓
上报执行结果到父节点
    ↓
循环（按配置的间隔）
```

### 3. 认证流程

级联系统使用自定义的 AK/SK 认证：

1. 子节点配置从父节点获取的 `api_key` 和 `api_secret`
2. 发送请求时在 `Authorization` 头中携带：`AK-SK {api_key}:{api_secret}`
3. 父节点验证凭证（通过哈希比对）
4. 验证通过后允许访问同步接口

## 使用场景

### 场景1：扩展采集能力

- **父节点**：负责管理公众号、消息任务，接收采集结果
- **子节点**：多个子节点分布在不同网络环境，采集文章并推送

### 场景2：多地域部署

- **父节点**：集中式管理
- **子节点**：部署在不同地区，提供低延迟服务

### 场景3：负载均衡

- **父节点**：分发任务
- **子节点**：分担采集和推送压力

## 注意事项

1. **安全性**：
   - API Secret 仅在生成时显示一次，请妥善保存
   - 建议使用 HTTPS 通信
   - 定期更换子节点凭证

2. **网络**：
   - 确保子节点能够访问父节点的 API 地址
   - 注意防火墙和网络策略配置

3. **同步策略**：
   - 同步间隔不宜过短，避免对父节点造成压力
   - 建议根据业务量调整 `sync_interval`

4. **故障处理**：
   - 子节点离线时，父节点会在心跳间隔后自动标记为离线
   - 子节点会自动重连父节点

## 故障排查

### 子节点无法连接父节点

1. 检查父节点是否正常运行
2. 确认 `parent_api_url` 配置正确
3. 检查网络连通性
4. 验证 API 凭证是否正确

### 数据未同步

1. 查看子节点日志，确认同步服务已启动
2. 检查父节点是否配置了相应的公众号和任务
3. 查看同步日志 `/api/v1/cascade/sync-logs`

### 认证失败

1. 确认使用的是正确的 `api_key` 和 `api_secret`
2. 检查子节点状态是否为启用状态
3. 验证 Authorization 头格式是否正确

## 示例代码

### 手动触发同步（Python）

```python
import asyncio
from jobs.cascade_sync import cascade_sync_service

async def manual_sync():
    cascade_sync_service.initialize()
    await cascade_sync_service.full_sync()

asyncio.run(manual_sync())
```

### 查看子节点状态（Shell）

```bash
# 通过API查询
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://parent-server:8001/api/v1/cascade/nodes

# 查看同步日志
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://parent-server:8001/api/v1/cascade/sync-logs
```
