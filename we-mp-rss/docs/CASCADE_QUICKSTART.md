# WeRSS 级联系统快速开始

## 1. 父节点部署（主服务器）

### 步骤1：初始化数据库

```bash
# 确保数据库配置正确
# config.yaml
db: sqlite:///data/db.db

# 运行初始化脚本
python jobs/cascade_init.py --init
```

### 步骤2：创建子节点

```bash
# 创建子节点
python jobs/cascade_init.py --child "子节点1" --desc "用于扩展采集" --api-url "http://child-node:8001"
```

系统会输出：
```
==================================================
子节点凭证 (请妥善保存，仅显示一次)
==================================================
节点ID: 550e8400-e29b-41d4-a716-446655440000
API Key: CNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
API Secret: CSxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
==================================================

请将以下配置添加到子节点的 config.yaml:

cascade:
  enabled: true
  node_type: child
  parent_api_url: http://parent-server:8001
  api_key: CNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  api_secret: CSxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 步骤3：启动父节点

```bash
python main.py
```

### 步骤4：管理子节点

```bash
# 查看所有节点
python jobs/cascade_init.py --list

# 通过API查看（需要登录）
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8001/api/v1/cascade/nodes

# 查看同步日志
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8001/api/v1/cascade/sync-logs
```

## 2. 子节点部署（工作节点）

### 步骤1：配置级联参数

编辑 `config.yaml`：

```yaml
cascade:
  enabled: true
  node_type: child
  parent_api_url: "http://parent-server:8001"  # 父节点地址
  api_key: "CNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # 从父节点获取
  api_secret: "CSxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # 从父节点获取
  sync_interval: 300  # 5分钟同步一次
  heartbeat_interval: 60  # 60秒心跳一次
```

或使用环境变量：

```bash
export CASCADE_ENABLED=True
export CASCADE_NODE_TYPE=child
export CASCADE_PARENT_URL=http://parent-server:8001
export CASCADE_API_KEY=CNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export CASCADE_API_SECRET=CSxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 步骤2：启动子节点

```bash
python main.py
```

子节点将自动：
1. 连接到父节点
2. 拉取公众号数据
3. 拉取消息任务
4. 执行任务并上报结果

## 3. 验证部署

### 父节点端检查

```bash
# 检查子节点状态
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8001/api/v1/cascade/nodes

# 查看同步日志
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8001/api/v1/cascade/sync-logs
```

预期响应：
```json
{
  "code": 0,
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "node_type": 1,
      "name": "子节点1",
      "status": 1,
      "last_heartbeat_at": "2024-01-01T10:00:00"
    }
  ]
}
```

### 子节点端检查

```bash
# 查看日志，应看到：
# 级联同步服务已启动，父节点地址: http://parent-server:8001
# 公众号同步完成，共同步 X 条
# 消息任务同步完成，共同步 Y 条
```

## 4. 常用命令

### 父节点

```bash
# 初始化数据库
python jobs/cascade_init.py --init

# 创建子节点（会自动生成凭证）
python jobs/cascade_init.py --child "节点名称" --desc "描述"

# 查看所有节点
python jobs/cascade_init.py --list

# 检查配置
python jobs/cascade_init.py --check
```

### 通过API管理

```bash
# 获取子节点凭证（如果忘记）
POST /api/v1/cascade/nodes/{node_id}/credentials
Authorization: Bearer {token}

# 测试节点连接
POST /api/v1/cascade/nodes/{node_id}/test-connection
Authorization: Bearer {token}
{
  "api_url": "http://child-node:8001",
  "api_key": "CNxxxxx",
  "api_secret": "CSxxxxx"
}

# 获取同步日志
GET /api/v1/cascade/sync-logs?limit=50
Authorization: Bearer {token}
```

### 子节点

```bash
# 检查配置
python jobs/cascade_init.py --check

# 启动服务（会自动连接父节点）
python main.py
```

## 5. 故障排查

### 子节点无法连接父节点

1. 检查父节点是否启动：`curl http://parent-server:8001/api/v1/health`
2. 检查网络连通性
3. 验证 API 凭证是否正确
4. 查看父节点日志

### 数据未同步

1. 确认父节点有公众号和消息任务数据
2. 查看子节点日志，检查同步服务是否启动
3. 检查配置中的同步间隔是否合理
4. 查看同步日志排查错误

### 心跳超时

1. 检查网络延迟
2. 增加 `heartbeat_interval` 配置值
3. 检查防火墙设置

## 6. 生产环境建议

1. **安全性**：
   - 使用 HTTPS 通信
   - 定期更换子节点凭证
   - 限制子节点访问权限

2. **性能**：
   - 根据业务量调整同步间隔
   - 监控网络带宽和延迟
   - 合理规划子节点数量

3. **监控**：
   - 监控心跳状态
   - 监控同步延迟
   - 设置告警机制

4. **备份**：
   - 定期备份父节点数据库
   - 记录子节点凭证（丢失后需要重新生成）

## 7. API文档

完整的API文档可以在服务启动后访问：
- Swagger UI: `http://localhost:8001/api/docs`
- ReDoc: `http://localhost:8001/api/redoc`

## 8. 示例架构

```
                    ┌─────────────────┐
                    │   父节点        │
                    │  (主服务器)     │
                    │                 │
                    │  - 公众号管理   │
                    │  - 任务管理     │
                    │  - 结果汇总     │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
  ┌──────────┐       ┌──────────┐        ┌──────────┐
  │ 子节点1   │       │ 子节点2   │        │ 子节点3   │
  │ (采集A)   │       │ (采集B)   │        │ (采集C)   │
  └──────────┘       └──────────┘        └──────────┘
```

## 9. 下一步

- 阅读详细文档：`docs/CASCADE_GUIDE.md`
- 查看API文档：`http://localhost:8001/api/docs`
- 配置消息推送（钉钉、飞书、企业微信等）
- 设置定时任务自动执行
