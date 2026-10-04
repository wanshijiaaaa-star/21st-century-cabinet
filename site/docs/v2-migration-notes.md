# V2 Migration Notes

本文件只分析 AI-assisted Information Processing 的演进路线，不代表已经批准或实现。V1.0 不应提前加入 AI SDK、API Key、向量数据库、队列或 AI 字段。

## 1. 当前架构能否支持 AI

可以支持个人规模的试验，但需要先建立清晰的后台任务边界。

可以直接复用：

- Source、Article 的人工等级和批红规则；
- 已清洗的标题、摘要、正文和发布时间；
- `article_content` 中的纯文本与 `content_hash`；
- 收藏、阅读进度、批注等人工反馈信号；
- 现有后台线程与状态 API 的交互模式；
- SQLite 本机存储和备份。

需要谨慎的部分：

- Source/Article 当前存于单个 JSON，AI 状态不适合继续堆入该 JSON；
- AI 处理必须异步，不能阻塞 Feed Sync 或 Reader；
- 正文抓取失败、内容更新和重复处理需要独立状态；
- 用户可能不希望正文发送给云端模型，必须明确本地/云端边界。

## 2. Article Model 未来可能需要的字段

不要在 V1 数据库中提前添加。V2 可考虑独立表 `article_ai`：

| 字段 | 建议含义 |
| --- | --- |
| `article_id` | Article ID，逻辑唯一 |
| `content_hash` | 处理时正文版本，内容变化后自动失效 |
| `provider`、`model` | 生成来源 |
| `status` | `pending` / `processing` / `ready` / `failed` |
| `ai_summary` | AI 摘要 |
| `ai_tags_json` | 建议标签，不直接覆盖人工标签 |
| `relevance_score` | 可选兴趣相关度 |
| `relevance_reason` | 可解释理由 |
| `error` | 失败原因 |
| `processed_at` | 完成时间 |

如果继续使用 JSON 状态，至少也应把 AI 结果放在独立表中，避免每个后台结果都重写整份 Source/Article 状态。

## 3. AI Service 放置位置

基于当前 Python 本机服务，建议：

```text
site/
├─ ai/
│  ├─ service.py          # 提供商无关入口
│  ├─ prompts.py          # 可版本化提示词
│  ├─ providers.py        # 本地或云端模型适配
│  └─ schemas.py          # 结构化输出校验
└─ jobs/
   └─ ai_processing.py    # 后台调度
```

不要把 AI 请求写进前端，也不要放进 `we-mp-rss`。采集器负责稳定取得原始内容，内阁负责用户语义与信息处理。

## 4. Background Processing

一百篇新文章的建议流程：

```text
Feed Sync
→ 新增 Article
→ 正文可用性检查
→ 创建 pending AI job
→ 限流 worker 逐篇处理
→ 按 content_hash 幂等保存
→ UI 轮询或读取状态
```

第一版可以使用 SQLite jobs 表与 1–2 个本机 worker，不必立即引入 Redis 或外部消息队列。需要包含：

- 幂等键：`article_id + content_hash + task_type + prompt_version`；
- 重试上限和退避；
- 启动时恢复卡在 `processing` 的任务；
- 并发与速率限制；
- 暂停、失败和手工重试；
- 成本与隐私提示。

## 5. Event Clustering

多个公众号报道同一事件时，可新增：

```text
clusters
  id
  title
  summary
  created_at
  updated_at

cluster_articles
  cluster_id
  article_id
  confidence
  assigned_by   # manual / ai
```

聚类建议分两阶段：

1. 时间窗口、标题关键词和来源差异做候选召回；
2. 模型判断是否属于同一事件。

必须允许用户拆分、合并和手工覆盖，AI 不应删除原文章或改变其阅读状态。

## 6. Daily Digest

日报可以建立在指定时间窗口的 Article 上：

1. 选择未读、收藏或用户允许的来源范围；
2. 优先复用单篇 AI 摘要；
3. 对事件 Cluster 去重；
4. 生成按主题或来源分组的 Digest；
5. 每一条始终链接回 Article 和原文。

建议保存 Digest 快照和生成参数，避免每次打开结果变化，也便于追踪来源。

## 7. Inbox / 批红原则

V1 基础规则必须保留：

```text
来源默认规则 + 单篇人工覆盖
```

V2 的 AI 最好提供：

- “建议加入批红”；
- 相关度分数与理由；
- 可选的辅助排序；
- 用户主动启用的增强过滤。

AI 不应默认执行：

- 无条件把文章加入或移出批红；
- 覆盖 `manualInbox`；
- 根据阅读行为暗中改变来源规则；
- 自动标记已读或删除文章。

推荐优先级：

```text
用户单篇决定
> 用户来源规则
> AI 建议
```

## 8. V2 前置工作建议

在接入任何模型前，先完成：

1. 把 Source/Article 从 JSON 状态迁移到版本化关系表，或至少增加稳定的数据访问层；
2. 为批红、Continue、Saved、去重和保留策略补充自动化测试；
3. 明确本地模型与云端模型的隐私策略；
4. 建立可恢复的后台任务表；
5. 设计模型结果失效与重新处理规则。

