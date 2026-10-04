# 微信读书公众号采集

当公众号后台接口不可用时，可以把采集模式切换为微信读书 Web。该模式直接请求 `weread.qq.com`，不经过第三方中转，并继续使用现有的 `MP_WXS_*` Feed ID 和 RSS 地址。

## 配置

1. 登录 `https://weread.qq.com`，打开任意公众号页面。
2. 在浏览器开发者工具的 Network 面板找到 `/api/mp/cover` 请求（旧版 `/web/mp/articles` 已被微信读书废弃）。
3. 从 Request Headers 复制完整 `Cookie`（新版不需要 `x-wr-ticket`）。
4. 在管理页的“微信读书公众号采集”中保存，或设置环境变量：

```env
GATHER.MODEL=weread_mp
WEREAD_COOKIE=wr_vid=...; wr_skey=...; wr_rt=...
WEREAD_CONTENT_INTERVAL=2
```

需要在 RSS 中直接显示全文时，同时设置：

```env
GATHER.CONTENT=True
```

## 行为

- 新版微信读书已废弃 `/web/mp/articles` 列表接口（实测恒返回 `-2041`），前端 JS 中也不再有文章列表接口。
- 最新文章来自 `GET https://weread.qq.com/api/mp/cover?bookId=`，一次只返回该公众号**最新一篇**文章（`reviewId` + 标题 + 封面）。
- 全文来自 `GET https://weread.qq.com/web/mp/content?reviewId=`，并提取 `#js_content`。
- 采用「cover 增量」采集：每次运行取最新一篇，若该 `reviewId` 已入库则跳过；新文章拉取正文后入库并更新 Feed 同步时间。
- 正文请求失败的文章以空正文入库（RSS 仍可点击原文链接），下一轮遇到同一文章会跳过，不会重复请求。
- `-2041`、`-2012` 和 `-2010` 会明确报告为认证或风控错误，不立即重试。

## 划线 / 笔记采集（weread 模式）

- `GATHER.MODEL=weread` 时采集**书架电子书**的划线/笔记（`/web/book/bookmarklist`）。
- 公众号订阅书（`MP_WXS_*`）在微信读书内没有划线数据，划线模式下会自动跳过并提示。
- 手动「采集」接口（`/weread/collect`）会自动分档：指定 `MP_WXS_*` bookId 时走公众号文章采集，普通电子书走划线采集。

## 限制

- 拿不到历史文章列表：`/api/mp/cover` 只返回最新一篇，无法回补公众号历史文章（旧版列表接口已废弃）。
- Cookie 过期时（返回 `-2012`/`-2041`），应从浏览器重新复制 Cookie；通过环境变量提供的凭据优先于管理页保存值，管理页会标记为部署配置托管。
- 微信读书有访问频率限制，全文请求间隔建议保持 `WEREAD_CONTENT_INTERVAL >= 2`。
