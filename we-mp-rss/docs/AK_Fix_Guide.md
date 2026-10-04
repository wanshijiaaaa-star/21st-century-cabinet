# AK 认证修复指南

## 问题原因

之前实现了 AK (Access Key) 认证系统，但存在一个关键问题：

**所有 API 端点仍然使用 `get_current_user` 依赖，而不是 `get_current_user_or_ak`**。

虽然 `core/auth.py` 中已经定义了支持 AK 认证的 `get_current_user_or_ak` 函数，但各个 API 模块 (`apis/*.py`) 没有使用它，导致 AK 认证无法生效。

## 解决方案

将所有需要认证的 API 端点从使用 `get_current_user` 改为使用 `get_current_user_or_ak`。

### 修改的文件列表

以下文件已经更新以支持 AK 认证：

1. `apis/article.py` - 文章管理接口
2. `apis/cache.py` - 缓存管理接口
3. `apis/config_management.py` - 配置管理接口
4. `apis/export.py` - 导入/导出接口
5. `apis/message_task.py` - 消息任务接口
6. `apis/mps.py` - 公众号管理接口
7. `apis/sys_info.py` - 系统信息接口
8. `apis/tags.py` - 标签管理接口
9. `apis/tools.py` - 工具接口
10. `apis/user.py` - 用户管理接口

### 未修改的文件

以下文件保持不变（有意为之）：

- `apis/auth.py` - AK 管理接口仍然使用 JWT 认证（出于安全考虑）
- `apis/rss.py` - RSS 接口中的认证已注释（根据注释说明是有意开放的）

### 修改内容

#### 1. 导入语句
```python
# 修改前
from core.auth import get_current_user

# 修改后
from core.auth import get_current_user_or_ak
```

#### 2. 依赖注入
```python
# 修改前
@router.get("/example")
async def example_endpoint(
    current_user: dict = Depends(get_current_user)
):
    ...

# 修改后
@router.get("/example")
async def example_endpoint(
    current_user: dict = Depends(get_current_user_or_ak)
):
    ...
```

## AK 认证工作原理

### `get_current_user_or_ak` 函数

位于 `core/auth.py:335-381`，工作流程：

1. **优先检查 AK/SK 认证**
   - 从 `Authorization` 头提取认证信息
   - 如果格式为 `AK-SK ak_value:sk_value`，则解析并验证
   - 调用 `authenticate_ak(ak, sk)` 验证凭据

2. **回退到 JWT Token 认证**
   - 如果 AK/SK 认证失败或不存在，则使用 JWT Token
   - 从 `Authorization` 头提取 Bearer Token
   - 解码并验证 JWT

3. **返回用户信息**
   - AK 认证成功时，返回包含 `auth_type: "ak"` 的用户信息
   - JWT 认证成功时，返回包含 `auth_type: "jwt"` 的用户信息

### AK 验证流程

`authenticate_ak` 函数 (`core/auth.py:281-332`)：

1. 通过 `get_ak_by_key(access_key)` 查询数据库
2. 检查 AK 是否激活且未过期 (`is_valid()`)
3. 使用 SHA256 验证 Secret Key
4. 获取关联的用户信息
5. 更新 AK 的最后使用时间
6. 解析 AK 的权限设置
7. 返回用户信息

## 使用 AK 认证

### 请求格式

```http
GET /api/v1/mps HTTP/1.1
Host: example.com
Authorization: AK-SK WKabc123...:SKxyz456...
Content-Type: application/json
```

### Python 示例

```python
import requests

headers = {
    "Authorization": "AK-SK WKabc123...:SKxyz456...",
    "Content-Type": "application/json"
}

response = requests.get(
    "https://your-api.com/api/v1/mps",
    headers=headers
)

data = response.json()
print(data)
```

### 测试脚本

使用提供的测试脚本验证 AK 认证：

```bash
# 方法 1: 使用现有的 AK
python test_ak_auth.py --access-key "WK..." --secret-key "SK..."

# 方法 2: 登录创建新的 AK
python test_ak_auth.py --username "admin" --password "password"
```

## 安全考虑

1. **AK 管理接口使用 JWT 认证**
   - `/api/v1/auth/ak/*` 接口仍然需要 JWT Token
   - 防止使用 AK 管理其他 AK

2. **Secret Key 安全存储**
   - SK 使用 SHA256 哈希存储
   - 只在创建时返回明文 SK（仅一次）
   - 数据库中不保存明文 SK

3. **权限控制**
   - 每个 AK 可以设置独立的权限列表
   - 支持权限细粒度控制
   - 支持过期时间设置

## 故障排查

### AK 认证失败

1. **检查 Authorization 头格式**
   - 必须是 `AK-SK ak_value:sk_value`
   - 注意 AK 和 SK 之间用冒号分隔

2. **检查 AK 状态**
   - AK 必须是激活状态 (`is_active = True`)
   - AK 不能过期 (`expires_at` 为 None 或大于当前时间)

3. **检查 Secret Key**
   - Secret Key 对比使用 SHA256 哈希
   - 确保使用创建时返回的 SK（不是哈希值）

4. **检查 API 端点**
   - 确认端点使用 `get_current_user_or_ak`
   - AK 管理接口 (`/api/v1/auth/ak/*`) 需要 JWT Token

### 数据库检查

```sql
-- 查看 Access Keys
SELECT id, user_id, key, name, is_active, expires_at, last_used_at
FROM access_keys;

-- 检查 AK 状态
SELECT key, is_active, expires_at,
       CASE
           WHEN is_active = 0 THEN '已停用'
           WHEN expires_at IS NOT NULL AND expires_at < datetime('now') THEN '已过期'
           ELSE '正常'
       END as status
FROM access_keys;
```

## 兼容性

- ✅ **向后兼容**: 所有现有的 JWT Token 认证仍然有效
- ✅ **双认证**: 支持 JWT Token 和 AK/SK 两种认证方式
- ✅ **透明切换**: 客户端可以根据需求选择使用哪种认证方式

## 更新日志

- **2026-02-24**: 修复 AK 认证无法使用的问题
  - 更新所有 API 端点使用 `get_current_user_or_ak`
  - 创建测试脚本 `test_ak_auth.py`
  - 创建本修复指南文档
