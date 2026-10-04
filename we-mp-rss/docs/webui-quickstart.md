# Web UI 环境异常统计功能快速启动

## 前端已创建的文件

1. **API 接口**: `web_ui/src/api/envException.ts`
2. **页面组件**: `web_ui/src/views/EnvExceptionStats.vue`
3. **路由配置**: 已更新 `web_ui/src/router/index.ts`
4. **导航菜单**: 已更新 `web_ui/src/components/Layout/Navbar.vue`

## 快速启动步骤

### 1. 启动后端服务

确保后端服务已启动并且 Redis 已配置：

```bash
# 启动 Redis（如果未启动）
redis-server

# 或使用 Docker
docker run -d -p 6379:6379 --name redis redis:7-alpine

# 启动后端
cd f:\Wx\WeRss\we-mp-rss
python main.py
```

### 2. 编译前端

```bash
cd f:\Wx\WeRss\we-mp-rss\web_ui

# 安装依赖（如果未安装）
npm install

# 开发模式
npm run dev

# 或构建生产版本
npm run build
```

### 3. 访问页面

打开浏览器访问：
```
http://localhost:8001/env-exception
```

**注意**: 需要使用管理员账号登录

## 页面功能预览

### 统计概览
- 异常总数
- 异常URL数
- 受影响公众号数
- 统计日期

### 公众号异常统计
- 表格展示各公众号异常情况
- 支持排序和分页
- 颜色标签标识异常频率

### 异常URL列表
- 列出所有异常URL
- 可点击打开文章
- 显示异常时间

### 最近异常日志
- 列表展示最近20条日志
- 显示公众号信息和时间
- 可点击查看详情

## 测试功能

### 1. 模拟环境异常

运行测试脚本触发环境异常记录：

```bash
python quick_test_redis.py
```

### 2. 查看统计

访问 Web UI 页面查看统计数据。

### 3. API 测试

```bash
# 获取今日统计
curl -X GET "http://localhost:8001/api/env-exception/today" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 获取指定日期统计
curl -X GET "http://localhost:8001/api/env-exception/stats?date=2024-01-01" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 常见问题

### 1. 页面无法访问

检查：
- 后端服务是否启动
- 是否已登录
- 是否有管理员权限

### 2. 显示"暂无环境异常记录"

可能原因：
- Redis 未配置或连接失败
- 确实没有异常记录
- 选择了没有数据的日期

解决：
```bash
# 检查 Redis
python diagnose_redis.py

# 测试功能
python quick_test_redis.py
```

### 3. 数据加载失败

检查：
- 浏览器控制台错误信息
- 网络连接
- 后端服务日志

## 开发模式调试

### 启动开发服务器

```bash
cd web_ui
npm run dev
```

前端会在 http://localhost:5173 启动（默认端口）

### 配置开发环境代理

编辑 `web_ui/vite.config.ts`：

```typescript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
  // ... 其他配置
})
```

## 生产环境部署

### 构建前端

```bash
cd web_ui
npm run build
```

构建产物在 `web_ui/dist` 目录

### 后端配置

前端静态文件由后端服务提供，确保：

```yaml
# config.yaml
server:
  web_name: "WeRSS"
```

### 访问地址

```
http://your-domain/env-exception
```

## 相关文档

- [环境异常统计后端文档](./env-exception-stats.md)
- [Web UI 使用指南](./webui-env-exception-stats.md)
- [Redis 故障排查](./redis-troubleshooting.md)
