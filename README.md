# 21世纪内阁 · V1.0

“21世纪内阁”是一个单用户、本机优先的微信公众号与 RSS 阅读工具。它把信息源管理、未读队列、人工批红、站内阅读、收藏、阅读进度和札记保存在自己的电脑上。

> 当前版本：**V1.0**（语义版本 `1.0.0`）  
> 运行环境：Windows 10/11，本机 `127.0.0.1`  
> 本项目不是公网服务，请勿把 `4173` 或 `8001` 端口暴露到公网。

## 项目组成

```text
21st-century-cabinet/
├─ site/                  # 21世纪内阁主站
│  └─ data/               # 本机数据库与备份；不会上传 Git
└─ we-mp-rss/             # 公众号采集器及本项目的集成改动
   └─ data/               # 配置、数据库、Cookie 与缓存；不会上传 Git
```

`site` 与 `we-mp-rss` 必须保持为同级目录。公开仓库只包含程序；所有用户数据固定保存在上面两个 `data/` 目录中。

## Windows 快速开始

1. 双击根目录的 `安装环境.cmd`，创建独立 Python 环境并安装采集器依赖。
2. 双击 `site/启动公众号采集器.cmd`，首次启动时设置本机管理员密码。
3. 双击 `site/启动21世纪内阁.cmd`。
4. 打开 `http://127.0.0.1:4173/`。

采集器管理页位于 `http://127.0.0.1:8001/`。如采集方式需要 Playwright 浏览器，请参阅 [`site/README.md`](site/README.md) 中的完整安装说明。

## 隐私与数据

- 主站数据：`site/data/`
- 采集器数据与私有配置：`we-mp-rss/data/`
- 两个目录均被 Git 忽略，不会随正常的 `git add` 或 `git push` 上传。
- GitHub 不会备份这些被忽略的数据，请自行备份。
- 不要使用 `git add -f` 强制添加数据目录，也不要在未备份时运行 `git clean -fdx`。

发布或提交前可运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\privacy-check.ps1
```

## 文档

- [V2.0 发布交接与隐私检查](V2_RELEASE_HANDOFF.md)
- [完整使用与开发说明](site/README.md)
- [本机使用说明](site/本机使用说明.md)
- [系统架构](site/docs/architecture.md)
- [V1.0 状态](site/docs/v1-status.md)
- [更新记录](site/CHANGELOG.md)

## 上游与许可

主项目使用 [MIT License](LICENSE)。采集器来自
[rachelos/we-mp-rss](https://github.com/rachelos/we-mp-rss)，其 MIT License
保留在 [`we-mp-rss/LICENSE`](we-mp-rss/LICENSE)，详情见
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。
