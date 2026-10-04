# 配置缓存使用说明

## 概述

项目现已支持Redis、Memcached和内存缓存三种缓存方式，用于提升配置读取性能。

## 环境变量配置

### Redis缓存
```bash
# 启用Redis缓存
CACHE_TYPE=redis

# Redis连接配置
REDIS_HOST=localhost          # Redis服务器地址
REDIS_PORT=6379              # Redis端口
REDIS_DB=0                   # 数据库编号
REDIS_PASSWORD=              # Redis密码（可选）
```

### Memcached缓存
```bash
# 启用Memcached缓存
CACHE_TYPE=memcached

# Memcached连接配置
MEMCACHED_HOST=localhost     # Memcached服务器地址
MEMCACHED_PORT=11211         # Memcached端口
```

### 内存缓存（默认）
```bash
# 使用内存缓存（默认）
CACHE_TYPE=memory
```

## 配置文件示例

在 `config.yaml` 中配置缓存选项：

```yaml
cache:
  type: redis  # 可选: redis, memcached, memory
  dir: ./data/cache
  redis:
    host: localhost
    port: 6379
    db: 0
    password: ""
  memcached:
    host: localhost
    port: 11211
```

## 缓存机制

1. **优先从缓存读取**：每次配置读取都会先尝试从缓存获取
2. **自动同步**：配置文件修改后会自动同步到缓存
3. **缓存失效**：配置修改时会清除相关缓存并重新写入
4. **降级处理**：缓存失败时自动降级到内存缓存

## 缓存键结构

- 完整配置：`werss:config:full`
- 单个配置项：`werss:config:{key}`

## 缓存TTL

默认缓存时间为3600秒（1小时）

## 依赖安装

```bash
# Redis缓存依赖
pip install redis==5.2.1

# Memcached缓存依赖  
pip install pymemcache==4.0.0
```

## 使用示例

```python
from core.config import cfg

# 获取配置（自动从缓存读取）
app_name = cfg.get('app_name')

# 设置配置（自动同步到缓存）
cfg.set('debug', True)
```