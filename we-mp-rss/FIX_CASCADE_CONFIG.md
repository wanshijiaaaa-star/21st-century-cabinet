# 级联配置问题修复指南

## 当前问题

错误信息：
```
Request URL is missing an 'http://' or 'https://' protocol.
```

原因：`parent_api_url` 配置值格式不正确。

## 快速诊断

运行诊断脚本查看实际配置值：

```bash
python diagnose_config.py
```

## 常见问题及解决方案

### 问题1: URL包含多余引号

**症状：**
```
parent_api_url: '"http://localhost:8001"'
或
parent_api_url: 'http://localhost:8001'
```

**解决方案：**

#### 方案A: 修改 config.yaml（推荐）

编辑 `config.yaml` 文件，找到 cascade 部分：

```yaml
cascade:
  enabled: True
  node_type: child
  parent_api_url: "http://localhost:8001"  # ✓ 正确：有引号但配置解析器会处理
  # 或
  parent_api_url: http://localhost:8001      # ✓ 正确：无引号
  # 不要这样写：
  # parent_api_url: '"http://localhost:8001"'  # ✗ 错误：多余引号
  api_key: "CNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  api_secret: "CSxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  sync_interval: 300
  heartbeat_interval: 60
```

**注意：** 最新版本的代码已自动处理引号问题，会自动去除多余的引号。

#### 方案B: 使用环境变量

```bash
# Windows CMD
set CASCADE_PARENT_API_URL=http://localhost:8001

# Windows PowerShell
$env:CASCADE_PARENT_API_URL="http://localhost:8001"

# Linux/Mac
export CASCADE_PARENT_API_URL=http://localhost:8001
```

**注意：** 环境变量不要加引号！

### 问题2: URL缺少协议前缀

**症状：**
```
parent_api_url: 'localhost:8001'
```

**解决方案：**

最新版本的代码会自动添加 `http://` 前缀，但仍建议手动修正：

```yaml
cascade:
  parent_api_url: "http://localhost:8001"  # ✓ 正确
```

### 问题3: URL为空或未配置

**症状：**
```
parent_api_url: ''
或
parent_api_url: None
```

**解决方案：**

确保配置了完整的级联参数：

```yaml
cascade:
  enabled: True
  node_type: child
  parent_api_url: "http://your-parent-server:8001"
  api_key: "CNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  api_secret: "CSxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

## 完整配置示例

### 父节点配置

```yaml
cascade:
  enabled: True
  node_type: parent
  # 父节点不需要 parent_api_url、api_key、api_secret
```

### 子节点配置

```yaml
cascade:
  enabled: True
  node_type: child
  parent_api_url: "http://parent-server:8001"  # 替换为实际的父节点地址
  api_key: "CNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # 从父节点获取
  api_secret: "CSxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # 从父节点获取
  sync_interval: 300  # 同步间隔（秒）
  heartbeat_interval: 60  # 心跳间隔（秒）
```

## 获取父节点凭证

### 步骤1: 在父节点上创建子节点

```bash
# 在父节点服务器上运行
python jobs/cascade_init.py --child "子节点名称" --api-url "http://子节点地址:8001"
```

输出示例：
```
子节点凭证 (请妥善保存，仅显示一次)
==================================================
节点ID: xxx-xxx-xxx-xxx
API Key: CNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
API Secret: CSxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
==================================================
```

### 步骤2: 配置子节点

将输出的凭证配置到子节点的 `config.yaml` 中。

## 验证配置

### 方式1: 运行诊断脚本

```bash
python diagnose_config.py
```

应该看到：
```
✓ URL格式正确
```

### 方式2: 测试初始化

```bash
python test_cascade_init.py
```

应该看到：
```
✓ 级联客户端初始化成功
  - 父节点地址: http://localhost:8001
```

### 方式3: 测试连接

```bash
# 测试心跳
curl -X POST "http://parent:8001/api/v1/cascade/heartbeat" \
  -H "Authorization: AK-SK CNxxx:CSxxx"
```

## 配置格式说明

### YAML格式规则

```yaml
# ✓ 正确写法
parent_api_url: "http://localhost:8001"  # 有引号
parent_api_url: http://localhost:8001    # 无引号

# ✗ 错误写法
parent_api_url: '"http://localhost:8001"'  # 多余引号
parent_api_url: 'http://localhost:8001'    # 单引号（某些解析器可能出错）
parent_api_url: localhost:8001             # 缺少协议
```

### 环境变量格式规则

```bash
# ✓ 正确写法
export CASCADE_PARENT_API_URL=http://localhost:8001
export CASCADE_PARENT_API_URL="http://localhost:8001"

# ✗ 错误写法
export CASCADE_PARENT_API_URL='"http://localhost:8001"'
export CASCADE_PARENT_API_URL='http://localhost:8001'  # 单引号在shell中是字面量
```

## 自动修复功能

最新版本的代码包含自动修复功能：

1. **自动去除引号**: 清理配置值中的多余引号
2. **自动添加协议**: 如果URL缺少 `http://` 或 `https://`，自动添加 `http://`
3. **URL验证**: 验证最终的URL格式是否正确

修复代码位于 `core/cascade.py` 的 `_clean_url()` 方法。

## 常见错误对照表

| 配置值 | 问题 | 自动修复 | 建议 |
|--------|------|----------|------|
| `"http://localhost:8001"` | 无 | ✓ | 正确 |
| `http://localhost:8001` | 无 | ✓ | 正确 |
| `"localhost:8001"` | 缺少协议 | ✓ 自动添加 | 手动修改 |
| `'http://localhost:8001'` | 单引号 | ✓ 自动清理 | 手动修改 |
| `""http://localhost:8001""` | 多余引号 | ✓ 自动清理 | 手动修改 |
| `(空)` | 未配置 | ✗ | 必须配置 |

## 下一步

配置正确后：

1. **测试初始化**: `python test_cascade_init.py`
2. **启动子节点**: `python -m jobs.cascade_task_dispatcher child`
3. **查看任务**: `python examples/cascade_task_dispatcher_example.py check`

## 需要帮助？

如果问题仍然存在：

1. 运行 `python diagnose_config.py` 查看详细诊断信息
2. 检查环境变量是否正确设置
3. 确认父节点服务正常运行
4. 参考 `TROUBLESHOOTING_CASCADE.md`
