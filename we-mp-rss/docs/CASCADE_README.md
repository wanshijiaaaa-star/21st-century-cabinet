# WeRSS 级联系统完整实现

## 概述

WeRSS 级联系统是一个完整的父子节点架构，支持：

✅ 父子节点数据同步
✅ 级联AK/SK认证系统
✅ **智能任务分发**（根据节点空闲情况自动分配）
✅ 子节点任务执行与结果上报
✅ 节点管理和监控
✅ 同步日志记录

## 架构设计

### 核心组件

```
core/
├── models/
│   └── cascade_node.py       # 级联节点和同步日志模型
├── auth.py                   # 增强支持级联节点认证
└── cascade.py                # 级联管理器和客户端

apis/
└── cascade.py                # 级联管理API接口

jobs/
├── cascade_sync.py           # 子节点同步服务
├── cascade_task_dispatcher.py # 任务分发器（新增）
└── cascade_init.py          # 初始化脚本
```

### 数据模型

#### CascadeNode（级联节点表）
- `node_type`: 节点类型 (0=父节点, 1=子节点)
- `api_key/api_secret`: 认证凭证
- `parent_id`: 父节点ID
- `status`: 在线状态
- `sync_config`: 同步配置（包括容量、配额等）

#### CascadeSyncLog（同步日志表）
- `operation`: 操作类型
- `direction`: 数据方向 (pull/push)
- `status`: 同步状态
- `data_count`: 数据条数

## 功能特性

### 1. 认证系统

- **用户认证**: JWT Token
- **API认证**: Access Key (AK/SK)
- **级联认证**: 子节点专用 AK/SK

认证优先级：
```
级联节点AK/SK → 用户AK/SK → JWT Token
```

### 2. 父节点功能

- 管理子节点
- 生成子节点凭证
- 提供数据接口（公众号、任务）
- 接收任务执行结果
- 查看同步日志

### 3. 子节点功能

- 从父节点拉取数据
- 执行消息任务
- 上报执行结果
- 定期心跳保持连接

### 4. 数据同步

**Pull操作**（子节点 → 父节点）：
- 同步公众号数据
- 同步消息任务

**Push操作**（子节点 → 父节点）：
- 上报任务执行结果
- 发送心跳

## 快速开始

### 父节点部署

```bash
# 1. 初始化数据库
python jobs/cascade_init.py --init

# 2. 创建子节点（获取凭证）
python jobs/cascade_init.py --child "子节点1" --api-url "http://child:8001"

# 3. 启动父节点
python main.py
```

### 子节点部署

```yaml
# config.yaml
cascade:
  enabled: true
  node_type: child
  parent_api_url: "http://parent:8001"
  api_key: "CNxxxxxxxx"
  api_secret: "CSxxxxxxxx"
```

```bash
# 启动子节点
python main.py
```

## API接口

### 父节点管理接口

| 接口 | 方法 | 认证 | 说明 |
|------|------|------|------|
| /cascade/nodes | POST | JWT | 创建节点 |
| /cascade/nodes | GET | JWT | 获取节点列表 |
| /cascade/nodes/{id} | GET | JWT | 获取节点详情 |
| /cascade/nodes/{id} | PUT | JWT | 更新节点 |
| /cascade/nodes/{id} | DELETE | JWT | 删除节点 |
| /cascade/nodes/{id}/credentials | POST | JWT | 生成凭证 |
| /cascade/nodes/{id}/test-connection | POST | JWT | 测试连接 |
| /cascade/sync-logs | GET | JWT | 查看同步日志 |
| /cascade/dispatch-task | POST | JWT | **触发任务分发** |
| /cascade/allocations | GET | JWT | **查看任务分配** |

### 子节点调用接口

| 接口 | 方法 | 认证 | 说明 |
|------|------|------|------|
| /cascade/feeds | GET | 级联AK | 获取公众号 |
| /cascade/message-tasks | GET | 级联AK | 获取任务 |
| /cascade/report-result | POST | 级联AK | 上报结果 |
| /cascade/heartbeat | POST | 级联AK | 发送心跳 |
| /cascade/pending-tasks | GET | 级联AK | **获取待处理任务** |

## 配置说明

### 环境变量

```bash
# 父节点（默认）
CASCADE_ENABLED=False
CASCADE_NODE_TYPE=parent

# 子节点
CASCADE_ENABLED=True
CASCADE_NODE_TYPE=child
CASCADE_PARENT_URL=http://parent:8001
CASCADE_API_KEY=CNxxxxxxxx
CASCADE_API_SECRET=CSxxxxxxxx
CASCADE_SYNC_INTERVAL=300
CASCADE_HEARTBEAT_INTERVAL=60
```

### 配置文件

```yaml
cascade:
  enabled: true
  node_type: child
  parent_api_url: "http://parent:8001"
  api_key: "CNxxxxxxxx"
  api_secret: "CSxxxxxxxx"
  sync_interval: 300
  heartbeat_interval: 60
```

## 使用场景

### 1. 扩展采集能力

- 父节点统一管理
- 多个子节点分布采集
- 结果汇总到父节点

### 2. 多地域部署

- 子节点部署在不同地区
- 提供低延迟服务
- 统一数据管理

### 3. 负载均衡

- 父节点分发任务
- 子节点分担压力
- 横向扩展能力

## 安全性

1. **凭证管理**:
   - API Secret 仅生成时显示
   - 使用 SHA256 哈希存储
   - 支持凭证停用和删除

2. **认证机制**:
   - 双重AK/SK认证
   - 支持过期时间
   - 记录使用审计

3. **通信安全**:
   - 支持HTTPS
   - 请求头验证
   - 心跳检测

## 监控与日志

### 同步日志

```json
{
  "id": "log-id",
  "node_id": "node-id",
  "operation": "sync_feeds",
  "direction": "pull",
  "status": 1,
  "data_count": 10,
  "started_at": "2024-01-01T10:00:00",
  "completed_at": "2024-01-01T10:00:05"
}
```

### 状态监控

- 节点在线状态
- 最后心跳时间
- 最后同步时间
- 同步失败记录

## 故障排查

### 常见问题

1. **子节点无法连接**
   - 检查网络连通性
   - 验证凭证正确性
   - 查看父节点日志

2. **数据未同步**
   - 确认父节点有数据
   - 检查同步间隔配置
   - 查看同步日志

3. **认证失败**
   - 确认凭证未过期
   - 检查节点是否启用
   - 验证Authorization头格式

## 文档索引

- [快速开始指南](CASCADE_QUICKSTART.md)
- [完整使用指南](CASCADE_GUIDE.md)
- **[任务分发系统指南](CASCADE_TASK_DISPATCHER.md)** ⭐
- [API文档](http://localhost:8001/api/docs)

## 技术栈

- **后端框架**: FastAPI
- **数据库**: SQLAlchemy ORM
- **认证**: JWT + AK/SK
- **HTTP客户端**: httpx
- **异步**: asyncio

## 注意事项

1. 子节点凭证丢失后需要重新生成
2. 同步间隔不宜过短，避免对父节点压力
3. 建议使用HTTPS通信
4. 定期检查同步日志
5. 合理规划子节点数量

## 未来扩展

- [x] 支持父节点任务分发 ✅
- [x] 支持节点负载均衡 ✅
- [ ] 支持数据压缩传输
- [ ] 支持断点续传
- [ ] 支持节点动态注册

## 许可证

本项目遵循 WeRSS 主项目的许可证。
