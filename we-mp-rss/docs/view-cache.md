# 视图缓存使用说明

## 概述

为 views 目录下的页面添加了缓存功能，以提高页面加载速度和减少数据库查询压力。

## 已添加缓存的页面

### 1. 首页 (`/views/home`)
- **缓存键**: `home_page`
- **缓存时间**: 30分钟
- **缓存内容**: 标签列表、分页信息等

### 2. 文章列表页 (`/views/articles`)
- **缓存键**: `articles_list`
- **缓存时间**: 30分钟
- **缓存内容**: 文章列表、筛选信息、分页信息等

### 3. 文章详情页 (`/views/article/{article_id}`)
- **缓存键**: `article_detail`
- **缓存时间**: 1小时
- **缓存内容**: 文章内容、相关文章等

### 4. 标签详情页 (`/views/tag/{tag_id}`)
- **缓存键**: `tag_detail`
- **缓存时间**: 40分钟
- **缓存内容**: 标签信息、关联文章列表等

## 配置选项

在 `config.yaml` 中可以配置视图缓存：

```yaml
cache:
  # 视图缓存配置
  views:
    # 是否启用视图缓存，默认为True
    enabled: true
    # 视图缓存目录，默认为./data/cache/views
    dir: ./data/cache/views
    # 视图缓存过期时间，默认为1800秒（30分钟）
    ttl: 1800
```

## 缓存自动失效

缓存会在以下情况自动清除：

### 1. 文章相关操作
- 更新文章阅读状态 (`PUT /articles/{article_id}/read`)
- 清理无效文章 (`DELETE /articles/clean`)
- 清理重复文章 (`DELETE /articles/clean_duplicate_articles`)

### 2. 标签相关操作
- 创建新标签 (`POST /tags`)
- 更新标签 (`PUT /tags/{tag_id}`)
- 删除标签 (`DELETE /tags/{tag_id}`)

## 手动清除缓存

### API 接口

#### 清除所有视图缓存
```bash
DELETE /cache/clear
```

#### 清除指定模式的缓存
```bash
DELETE /cache/clear/{pattern}
```

示例：
```bash
# 清除所有文章列表缓存
DELETE /cache/clear/articles_list

# 清除所有首页缓存
DELETE /cache/clear/home_page
```

## 缓存存储

缓存文件存储在配置的缓存目录中（默认：`./data/cache/views`），每个缓存文件都是 pickle 格式的二进制文件。

## 缓存键生成规则

缓存键由以下部分组成：
- 前缀（如 `home_page`, `articles_list` 等）
- 参数的哈希值（确保不同参数组合有不同的缓存）

例如：
- `home_page_1a2b3c4d5e6f...` （首页第1页，每页12条）
- `articles_list_7g8h9i0j1k2l...` （文章列表，特定筛选条件）

## 注意事项

1. **缓存一致性**: 当数据更新时，相关缓存会自动清除，确保数据一致性。

2. **缓存大小**: 缓存文件会占用磁盘空间，建议定期清理旧的缓存文件。

3. **开发调试**: 在开发环境中，可以设置 `cache.views.enabled: false` 来禁用缓存。

4. **性能优化**: 合理的缓存时间设置可以在性能和数据实时性之间取得平衡。

## 故障排除

如果遇到缓存相关的问题：

1. 检查缓存目录权限
2. 确认磁盘空间充足
3. 检查配置文件中的缓存设置
4. 使用清除缓存API手动清除缓存

## 扩展使用

如果需要为其他页面添加缓存，可以参考现有实现：

```python
from core.cache import cache_view

@cache_view("your_page_prefix", ttl=1800)
async def your_view_function():
    # 视图逻辑
    pass
```