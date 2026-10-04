# Access Key 管理 UI 使用指南

## 概述

WeRSS 现已支持 Access Key (AK) 认证方式，用于程序化访问 API。本 UI 界面提供了完整的 AK 管理功能。

## 功能特性

### 1. 创建 Access Key
- 为应用程序或脚本生成 API 凭证
- 支持自定义 AK 名称和描述
- 可设置权限范围（读、写、删除、管理）
- 支持配置过期时间

### 2. 查看 Access Key 列表
- 列表显示所有已创建的 Access Keys
- 显示状态：活跃、已停用、已过期
- 显示最后使用时间（用于审计）
- 显示权限和过期时间

### 3. 管理 Access Key
- **编辑**：修改 AK 名称、描述和权限
- **复制**：一键复制 Access Key 值
- **停用**：临时禁用 AK（保留记录）
- **删除**：永久删除 AK 记录

## 使用步骤

### 创建 Access Key

1. 点击"创建 Access Key"按钮
2. 填写以下信息：
   - **AK 名称**（必填）：例如"生产环境爬虫"
   - **描述**（可选）：用途说明和备注
   - **权限范围**（可选）：选择所需权限
   - **过期时间**（可选）：指定天数后过期

3. 点击"确定"创建
4. 复制显示的 **Secret Key**，**此密钥只会显示一次**

### 在应用中使用

#### Python 示例

```python
import requests

access_key = "WK_YOUR_KEY"
secret_key = "SK_YOUR_SECRET"

# 构建 Authorization 头
auth_header = f"AK-SK {access_key}:{secret_key}"

# 发起请求
response = requests.get(
    'http://your-api-url/api/v1/wx/articles',
    headers={'Authorization': auth_header}
)

print(response.json())
```

#### cURL 示例

```bash
curl -H "Authorization: AK-SK WK_YOUR_KEY:SK_YOUR_SECRET" \
     http://your-api-url/api/v1/wx/articles
```

#### JavaScript/Node.js 示例

```javascript
const axios = require('axios');

const accessKey = 'WK_YOUR_KEY';
const secretKey = 'SK_YOUR_SECRET';

const api = axios.create({
  baseURL: 'http://your-api-url/api/v1',
  headers: {
    'Authorization': `AK-SK ${accessKey}:${secretKey}`
  }
});

api.get('/wx/articles').then(res => {
  console.log(res.data);
});
```

## 安全建议

1. **妥善保管 Secret Key**
   - 创建时只会显示一次
   - 不要在公开场合暴露
   - 定期轮换重要应用的密钥

2. **最小权限原则**
   - 为每个应用创建独立的 AK
   - 只赋予必要的权限
   - 限制 AK 的使用范围

3. **设置过期时间**
   - 为安全起见，建议设置合理的过期时间
   - 定期更新过期的密钥

4. **监控使用情况**
   - 查看"最后使用"时间
   - 定期检查未使用的 AK
   - 停用或删除不需要的 AK

## API 端点

所有 AK 管理操作均需要有效的 JWT Token 认证。

| 操作 | 方法 | 端点 |
|------|------|------|
| 创建 AK | POST | `/api/v1/wx/auth/ak/create` |
| 查询列表 | GET | `/api/v1/wx/auth/ak/list` |
| 更新 AK | PUT | `/api/v1/wx/auth/ak/{ak_id}` |
| 停用 AK | POST | `/api/v1/wx/auth/ak/{ak_id}/deactivate` |
| 删除 AK | DELETE | `/api/v1/wx/auth/ak/{ak_id}` |

## 常见问题

**Q: Secret Key 丢失了怎么办？**
A: Secret Key 不可恢复。需要删除旧密钥，创建新的 AK。

**Q: 如何轮换密钥？**
A: 创建新 AK 并切换应用配置，然后删除旧 AK。

**Q: AK 支持哪些权限？**
A: 支持 read、write、delete、admin 等权限，具体取决于您的需求。

**Q: 过期的 AK 会自动删除吗？**
A: 不会。过期的 AK 会被标记为"已过期"但保留在列表中，需要手动删除。

## 技术细节

- AK/SK 认证优先级高于 JWT Token
- Secret Key 使用 SHA256 哈希存储，不可逆
- 每次使用时更新"最后使用"时间用于审计
- 支持权限细分，可覆盖用户默认权限
- 完全向后兼容 JWT Token 认证方式
