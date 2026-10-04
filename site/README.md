# 21世纪内阁

“21世纪内阁”是一个单用户、本机优先的信息源管理与长文阅读工具。V1.0 目前主要服务于微信公众号：由本机 `we-mp-rss` 采集器生成 RSS，内阁负责同步、筛选、批阅、站内阅读、收藏和札记。

> 当前真实运行栈是原生 HTML/CSS/JavaScript + Python 标准库 HTTP 服务 + SQLite。仓库中的 Vinext、Next.js、Drizzle 配置是早期 Sites 脚手架遗留，不是本机 V1.0 的运行链路。

## 目录关系

本机工作区需要保持两个同级目录：

```text
21世纪内阁/
├─ site/                  # 主站、Python 服务和本机数据目录
└─ we-mp-rss/             # 公众号采集器及内阁集成改动
```

`site/local_server.py` 通过相对路径读取 `../we-mp-rss/data/db.db`，因此移动项目时应整体移动 `21世纪内阁` 文件夹，不要单独移动 `site`。

## 主要能力

- “奏章呈送”：显示全部未读文章，按发布日期倒序；同日按 A、B、C 级排序。
- “批红定案”：显示未读且符合来源 Inbox 规则或单篇人工选择的文章。
- 信息源：添加、编辑、删除、启停同步、等级、类型和 Inbox 开关。
- 采集器接入：从 `we-mp-rss` 已有公众号中选择尚未接入的来源。
- 阅读：后台调阅微信公众号正文，成功后站内阅读，失败时跳转原文。
- 阅读状态：进度保存、约 95% 自动已读、继续阅读、收藏。
- 批注：正文右键划线或写笔记，札记页按文章归拢。
- 本机数据：SQLite、每日自动备份、手动导出备份、90 天普通文章保留策略。

## 环境要求

- Windows 10/11。
- 主站：Python 3.11+；当前启动脚本按 Python 3.13+ 编写。
- 采集器：Python 3.13.x 及 `we-mp-rss/requirements.txt` 中的依赖。
- Node.js 20+ 仅用于修改并构建采集器 Vue 前端；日常使用不需要 Node。

主站不需要 `.env`。采集器使用被 Git 忽略的 `we-mp-rss/data/config.yaml`；密码、Cookie、授权信息和数据库也都保存在两个被忽略的 `data/` 目录中。

## 本机快速启动

在 `site` 目录依次双击：

1. `启动公众号采集器.cmd`
2. `启动21世纪内阁.cmd`

访问地址：

- 21世纪内阁：`http://127.0.0.1:4173/`
- 公众号采集器：`http://127.0.0.1:8001/`
- 采集器添加订阅：`http://127.0.0.1:8001/add-subscription`

两个命令窗口需要保持开启。关闭窗口即停止服务，已同步的数据不会丢失。

## 全新环境安装

### 1. 准备采集器

在 Windows 文件资源管理器中双击仓库根目录的 `安装环境.cmd`。在 PowerShell 中请运行 `.\安装环境.cmd`（必须带 `.\`）。它会创建本机虚拟环境、安装依赖，并从公开样例生成私有的 `we-mp-rss/data/config.yaml`。

也可以在 PowerShell 中手工执行：

```powershell
py -3.13 -m venv "$env:LOCALAPPDATA\CenturyCabinet\we-rss-venv"
& "$env:LOCALAPPDATA\CenturyCabinet\we-rss-venv\Scripts\python.exe" -m pip install -r .\we-mp-rss\requirements.txt
New-Item -ItemType Directory -Force .\we-mp-rss\data
Copy-Item .\we-mp-rss\config.example.yaml .\we-mp-rss\data\config.yaml
```

如采集模式需要 Playwright 浏览器，再执行：

```powershell
& "$env:LOCALAPPDATA\CenturyCabinet\we-rss-venv\Scripts\python.exe" -m playwright install chromium
```

首次双击 `site/启动公众号采集器.cmd` 时会要求设置本机管理员密码。密码只用于初始化本机采集器。

### 2. 启动主站

```powershell
cd .\site
python .\local_server.py
```

主站首次启动会创建 `site/data/cabinet.db`。

## 添加公众号

1. 准备目标公众号任意一篇公开文章链接。
2. 在采集器的“添加订阅”页面通过文章链接建立订阅。
3. 回到“21世纪内阁 → 信息源 → 从采集器选择”。
4. 勾选尚未接入的公众号并接入。
5. 在信息源卡片中设置等级、类型、同步状态和是否默认进入批红。

普通 `mp.weixin.qq.com/s/...` 链接不能直接填入 Feed URL。Feed URL 应是采集器生成的 `http://127.0.0.1:8001/feed/MP_WXS_数字.rss`。

## 数据与备份

- 主数据库：`site/data/cabinet.db`
- 自动备份：`site/data/backups/`
- 采集器数据库：`we-mp-rss/data/db.db`
- 普通文章保留 90 天；收藏、含札记、未读完或没有可靠发布时间的文章长期保留。
- “设置 → 数据保管 → 导出本机备份”可导出 SQLite 文件。

恢复数据库前先关闭两个服务。不要手工修改正在使用的数据库。

## 开发与验证

主站没有编译步骤，`dist/` 中的文件就是实际前端源码。常用检查：

```powershell
cd site
python -c "compile(open('local_server.py', encoding='utf-8').read(), 'local_server.py', 'exec')"
node --check .\dist\reader-features.js
```

采集器后端测试：

```powershell
cd we-mp-rss
& "$env:LOCALAPPDATA\CenturyCabinet\we-rss-venv\Scripts\python.exe" -m unittest discover -s tests -p "test_*.py"
```

采集器前端构建：

```powershell
cd we-mp-rss\web_ui
npm ci
npm run build
```

## 文档入口

- [项目概览](docs/project-overview.md)
- [系统架构](docs/architecture.md)
- [数据库与业务规则](docs/database.md)
- [V1.0 状态](docs/v1-status.md)
- [V1.0 发布审计](docs/release-audit.md)
- [V2 迁移分析](docs/v2-migration-notes.md)
- [更新记录](CHANGELOG.md)

## 版本状态

```text
Version: V1.0
Status: Stable local-first baseline
```

这是个人本机工具，不支持多用户、云端同步或公网部署。采集器前端依赖仍有待升级的安全公告，因此不要把 `4173` 或 `8001` 端口映射到公网。静态界面脱离本机 Python/SQLite 服务时只能作为演示页面使用。
