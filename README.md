# 21世纪内阁 · V1.0

“21世纪内阁”是一个单用户、本机优先的微信公众号与 RSS 阅读工具。它把信息源管理、未读队列、人工批红、站内阅读、收藏、阅读进度和札记保存在自己的电脑上。

> 当前版本：**V1.0**（语义版本 `1.0.1`）
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

## Windows 快速开始（推荐）

普通用户请从 GitHub Releases 下载 `21世纪内阁-安装程序-1.0.1.exe`：

1. 双击安装程序，单击“安装”；
2. 从桌面或开始菜单打开“21世纪内阁”；
3. 首次启动时在图形窗口中设置采集器管理员密码。

发行版自带私有运行时和全部依赖，不会安装 Python、Node.js 或 npm，不会修改系统 `PATH`，启动时也不会出现 CMD、PowerShell 或命令行窗口。主站和公众号采集器均由同一个入口在后台启动。

- 21世纪内阁：`http://127.0.0.1:4173/`
- 公众号采集器：`http://127.0.0.1:8001/`

安装程序会创建桌面和开始菜单入口。需要固定到任务栏或开始屏幕时，可在开始菜单搜索“21世纪内阁”并右键固定。

## 卸载

可从 Windows“已安装的应用”、开始菜单的“卸载21世纪内阁”，或发行包中的独立卸载程序完成卸载。卸载默认保留个人数据；只有主动勾选删除个人数据并再次确认，才会永久删除。

## 源码运行（仅开发者）

仓库中的 `安装环境.cmd`、`创建快捷方式.cmd` 和 `site/启动*.cmd` 只用于源码开发和维护，不会进入普通用户发行包。维护者的完整打包说明见 [`packaging/README.md`](packaging/README.md)。

## 隐私与数据

安装版数据统一位于 `%LOCALAPPDATA%\CenturyCabinet\Data`，与 `%LOCALAPPDATA%\Programs\CenturyCabinet` 中的程序文件分开。覆盖安装不会替换数据，普通卸载也不会删除数据。

源码运行模式的数据仍固定在：

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
