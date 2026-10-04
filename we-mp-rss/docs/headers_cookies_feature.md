# 消息任务 Headers 和 Cookies 认证功能

## 功能说明

为消息任务添加了 Headers 和 Cookies 字段支持，使 WebHook 可以调用需要认证的远程接口。

## 更新内容

### 1. 数据库模型 (core/models/message_task.py)

添加了两个新字段：
- `headers`: TEXT 类型，可选，用于存储 JSON 格式的请求头
- `cookies`: TEXT 类型，可选，用于存储 Cookie 字符串

### 2. 前端类型定义 (web_ui/src/types/messageTask.ts)

更新了三个接口：
- `MessageTask`: 添加 `headers` 和 `cookies` 可选字段
- `MessageTaskCreate`: 添加 `headers` 和 `cookies` 可选字段
- `MessageTaskUpdate`: 添加 `headers` 和 `cookies` 可选字段

### 3. 前端表单 (web_ui/src/views/MessageTaskForm.vue)

- 使用 Tab 形式组织表单，分为"基本配置"和"高级配置"
- "高级配置" Tab 中包含 Headers 和 Cookies 输入框
- Headers 字段支持 JSON 格式输入
- Cookies 字段支持标准 Cookie 字符串格式

### 4. 后端 API (apis/message_task.py)

更新了 `MessageTaskCreate` Pydantic 模型：
- 添加 `headers: Optional[str] = ""`
- 添加 `cookies: Optional[str] = ""`

更新了创建和更新接口：
- 创建消息任务时支持设置 headers 和 cookies
- 更新消息任务时支持修改 headers 和 cookies

### 5. WebHook 调用逻辑 (jobs/webhook.py)

`call_webhook` 函数更新：
- 解析用户提供的 JSON 格式 headers，并与默认 Content-Type 合并
- 解析用户提供的 Cookie 字符串，转换为字典格式
- 在发送 POST 请求时携带这些 headers 和 cookies

## 数据库迁移

如果数据库表已经存在，需要执行迁移脚本添加新字段：

```bash
python migrations/add_headers_cookies_fields.py
```

或者，系统启动时会自动调用 `DB.create_tables()`，这会为缺少的字段自动添加（使用 SQLAlchemy 的 metadata.create_all）。

## 使用示例

### Headers 格式

```json
{
  "Authorization": "Bearer your_token_here",
  "X-Custom-Header": "custom_value"
}
```

### Cookies 格式

```
session_id=abc123def456; auth_token=xyz789ghi012; user_pref=theme=dark
```

### 前端操作

1. 进入消息任务编辑页面
2. 点击"高级配置" Tab
3. 在 Headers 输入框中输入 JSON 格式的请求头
4. 在 Cookies 输入框中输入 Cookie 字符串
5. 点击提交

### 后端处理

当执行消息任务时，系统会：
1. 解析 JSON 格式的 headers，合并到请求头中
2. 解析 Cookie 字符串，转换为字典格式
3. 使用这些认证信息调用 WebHook 接口

## 注意事项

1. **Headers 格式**: 必须是有效的 JSON 格式，否则会跳过自定义 headers
2. **Cookies 格式**: 使用标准的 `key=value; key=value` 格式，系统会自动解析
3. **安全性**: Headers 和 Cookies 可能包含敏感信息，请妥善保管
4. **兼容性**: 这两个字段都是可选的，不影响现有功能
5. **默认值**: 如果不填写，这两个字段为空字符串，不影响正常调用

## 测试建议

1. 测试无认证的 WebHook（不填写 Headers 和 Cookies）
2. 测试仅使用 Headers 认证的 WebHook
3. 测试仅使用 Cookies 认证的 WebHook
4. 测试同时使用 Headers 和 Cookies 认证的 WebHook
5. 测试无效的 JSON 格式 Headers（应该优雅降级）
