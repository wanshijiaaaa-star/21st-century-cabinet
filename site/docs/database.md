# 数据库与业务规则

## Overview

项目包含两个独立 SQLite 数据库：

- `site/data/cabinet.db`：21世纪内阁的来源、文章状态、正文缓存和批注。
- `we-mp-rss/data/db.db`：公众号订阅、采集文章、用户与采集器内部任务。

两个 `data/` 目录均被 Git 忽略。当前没有 Prisma migration；主站由 `CabinetStore.__init__()` 使用 `CREATE TABLE IF NOT EXISTS` 管理表结构。

## cabinet.db

### kv

用途：保存主站的聚合状态。

| 字段 | 类型 | 约束 | 含义 |
| --- | --- | --- | --- |
| `key` | TEXT | PRIMARY KEY | 当前使用 `state` |
| `value` | TEXT | NOT NULL | JSON：`sources` 与 `articles` |

这是一种轻量 V1 实现，不是规范化关系模型。任何结构演进都需要兼容旧 JSON。

### Source JSON

实际字段：

| 字段 | 含义 |
| --- | --- |
| `id` | 本机来源 ID |
| `name` | 显示名称 |
| `description` | 来源说明 |
| `feedUrl` | RSS/Atom URL |
| `tier` | `A`、`B`、`C` |
| `category` | `NEWS`、`ACADEMIC`、`LONGFORM`、`COMMENTARY`、`TECH`、`OTHER` |
| `inbox` | 新未读文章是否默认进入批红 |
| `enabled` | 是否继续同步 |
| `articles` | 当前保留文章数的缓存统计 |
| `unread` | 当前未读数的缓存统计 |
| `last` | 面向 UI 的最近同步文案 |
| `lastSyncAt` | ISO 8601 最近同步时间，可空 |
| `lastError` | 最近同步错误，可空；当前 UI 不展示详情 |

Source 没有独立数据库 unique constraint。导入时使用标准化后的 `feedUrl` 去重。

### Article JSON

实际字段：

| 字段 | 含义 |
| --- | --- |
| `id` | 本机文章 ID |
| `source` | Source ID |
| `title`、`author`、`url` | 基础元数据 |
| `summary` | 最长约 76 字、以句号结尾的摘要，可空 |
| `publishedAt` | ISO 8601 发布时间，可空 |
| `cover` | 远程封面 URL，可空 |
| `mins` | 估算阅读分钟数 |
| `read` | 已读状态 |
| `saved` | 收藏状态 |
| `progress` | `0..1` 阅读进度 |
| `readingAnchor` | Reader 当前正文块位置，可空 |
| `tags` | 文章标签数组；V1 没有编辑 UI |
| `manualInbox` | 可空三态单篇批红覆盖 |
| `content` | Feed 文本的兼容字段；真实正文在 `article_content` |

同步去重优先比较文章 URL；URL 不可用时比较 `(source, title)`。现有文章同步时只刷新发布时间、摘要、作者、封面和阅读时长，保留阅读、收藏、进度与单篇批红状态。

### article_content

用途：缓存按需调阅的公众号正文。

| 字段 | 类型 | 约束 / 默认 | 含义 |
| --- | --- | --- | --- |
| `article_id` | TEXT | PRIMARY KEY | 对应 Article JSON 的 `id` |
| `source_url` | TEXT | NOT NULL | 微信原文 URL |
| `html` | TEXT | NOT NULL, `''` | 清理后的正文 HTML |
| `plain_text` | TEXT | NOT NULL, `''` | 纯文本正文 |
| `content_hash` | TEXT | NOT NULL, `''` | SHA-256 |
| `status` | TEXT | NOT NULL, `ready` | `loading` / `ready` / `failed` |
| `error` | TEXT | NOT NULL, `''` | 失败说明 |
| `fetched_at` | TEXT | NOT NULL | ISO 8601 时间 |

没有数据库外键。服务启动时会把遗留的 `loading` 状态改为 `failed`，避免永久卡住。

### annotations

用途：保存划线和笔记。

| 字段 | 类型 | 约束 / 默认 | 含义 |
| --- | --- | --- | --- |
| `id` | TEXT | PRIMARY KEY | 批注 ID |
| `article_id` | TEXT | NOT NULL | Article ID |
| `kind` | TEXT | NOT NULL | `highlight` 或 `note` |
| `quote` | TEXT | NOT NULL | 选中文字 |
| `prefix`、`suffix` | TEXT | NOT NULL, `''` | 上下文定位文本 |
| `block_index` | INTEGER | NOT NULL, `0` | Reader 正文块序号 |
| `start_offset`、`end_offset` | INTEGER | NOT NULL, `0` | 块内字符范围 |
| `note` | TEXT | NOT NULL, `''` | 笔记正文 |
| `created_at`、`updated_at` | TEXT | NOT NULL | ISO 8601 时间 |

索引：`idx_annotations_article_updated(article_id, updated_at DESC)`。

没有数据库外键。Reader 首先按块和偏移恢复批注；正文轻微变化时回退到块内 quote 搜索。

## Core Calculated Rules

### 批红资格

```text
if article.manualInbox === true:
    selected = true
else if article.manualInbox === false:
    selected = false
else:
    selected = source.inbox && source.enabled

批红定案 = article.read === false && selected
```

### 奏章呈送

```text
article.read === false
```

该页面名称来自产品主题，实际不是“只显示今天收到的文章”。排序先按上海时区自然日倒序，同日按 A、B、C，再按发布时间倒序。

### Continue

```text
0 < article.progress < 0.95
```

当前实现不额外检查 `read` 或批红状态。

### Saved

```text
article.saved === true
```

与来源是否进入批红无关。

### Retention

默认保留 90 天。满足以下任一条件的文章不会因过期被删除：

- 已收藏；
- 含批注；
- `0 < progress < 0.95`；
- 没有可靠发布时间。

## we-mp-rss Database

采集器使用 SQLAlchemy 模型。与内阁直接相关的主要表如下。

### feeds

- 主键：`id`，通常为 `MP_WXS_*`。
- 元数据：`mp_name`、`mp_cover`、`mp_intro`、`faker_id`。
- 状态：`status`（有索引）。
- 时间：`sync_time`、`update_time`、`created_at`、`updated_at`。

内阁的“从采集器选择”直接以只读方式查询此表，不读取管理员令牌。

### articles

- 主键：`id`。
- 关联：`mp_id`（有索引；逻辑关联 feeds，没有数据库外键）。
- 元数据：`title`、`pic_url`、`url`、`description`。
- 正文：`content`、`content_html`、`has_content`。
- 发布时间：`publish_time`（Unix 秒，有索引）。
- 状态：`status`、`is_read`、`is_favorite`、`fix_fail_count`、`fetch_started_at` 等。

采集器中还存在 `users`、`tags`、`message_tasks`、`message_tasks_logs`、`access_keys`、`filter_rules`、`config_management` 以及 cascade 相关表。这些属于上游采集器能力，主站 V1 不直接依赖。

## Backup and Migration Notes

- 主站每次状态保存后最多每天创建一次 `data/backups/cabinet-YYYY-MM-DD.db`。
- 手动导出使用 SQLite backup API，避免直接复制打开中的数据库。
- 当前没有版本化 migration 表。增加列或表时必须保持 `CREATE TABLE IF NOT EXISTS` 与旧数据库兼容，并补充显式迁移逻辑。
- `article_content` 与 `annotations` 无外键；来源删除或保留策略淘汰文章后可能留下孤立正文缓存，这是已知清理限制。

