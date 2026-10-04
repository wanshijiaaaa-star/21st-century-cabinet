# 21世纪内阁 V2.0 发布交接文档

本文档交给未来负责升级和发布 V2.0 的开发者或 AI 助手。目标是：**升级程序，但不把任何个人阅读数据、公众号订阅、Cookie、密码或本机配置上传到 GitHub。**

## 一、当前可直接使用的目录

当前公开版可以直接作为个人日常使用版本。程序代码位于本仓库，个人数据只允许写入以下两个目录：

```text
site/data/          # 主站数据：信息源、文章、批红、收藏、阅读进度、札记和备份等
we-mp-rss/data/     # 采集器数据：私有配置、数据库、Cookie、缓存和授权状态等
```

这两个目录会在首次运行或配置过程中自动创建，并已被根目录 `.gitignore` 忽略。GitHub 不会备份这些数据，用户需要自行备份。

## 二、V2.0 升级的基本原则

1. 程序代码可以更新，两个 `data/` 目录必须原地保留。
2. 新增的个人数据、密钥、Cookie、本机路径和私有配置，仍应放入上述两个 `data/` 目录，不得放在源码目录中。
3. 如 V2.0 需要改变数据库结构，应编写可重复执行的迁移程序；不要要求用户删除旧数据库重新开始。
4. 开始升级前，先停止主站和采集器，并把两个 `data/` 目录复制到仓库外的备份位置。
5. 先在备份或测试副本上验证迁移，再处理唯一的真实数据。

## 三、发布前必须完成的隐私检查

在仓库根目录运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\privacy-check.ps1
```

然后依次检查：

```powershell
# 两个 data 目录中的示例文件都应显示为 ignored。
git check-ignore -v site/data/privacy-test.txt
git check-ignore -v we-mp-rss/data/privacy-test.txt

# 此命令必须没有输出。
git ls-files site/data we-mp-rss/data

# 人工审查将要提交的文件名和内容。
git status --short
git diff --cached --stat
git diff --cached
```

如果 `git ls-files site/data we-mp-rss/data` 出现任何文件，立即停止发布。先用 `git rm --cached <文件>` 将其从 Git 索引中移除；不要删除用户磁盘上的真实数据。

还需要人工确认提交中没有以下内容：

- 真实公众号名称、账号 ID 或订阅清单；
- 数据库、备份、阅读记录、收藏和札记；
- Cookie、管理员密码、令牌、私钥或二维码；
- 用户名、本机绝对路径、内部部署地址；
- `.env`、`config.yaml`、日志或临时导出文件。

## 四、禁止操作

- 不要对个人数据使用 `git add -f`。
- 不要删除 `.gitignore` 中的 `/site/data/` 和 `/we-mp-rss/data/` 规则。
- 不要把数据目录移动到源码目录的其他位置以绕过忽略规则。
- 不要在没有仓库外备份时运行 `git clean -fdx`。
- 不要直接公开包含私人数据的旧 Git 历史；应从干净历史制作公开版本。
- 不要仅凭“文件现在已删除”就判断安全：曾提交过的内容仍可能存在于 Git 历史中。

## 五、V2.0 版本标记清单

准备 V2.0 时至少同步更新：

- 根目录 `VERSION`；
- `site/package.json` 和 `site/package-lock.json` 的版本号；
- README 与网页中显示的版本号；
- `site/CHANGELOG.md`；
- V2.0 状态或迁移说明文档；
- Git 标签，例如 `v2.0.0`。

建议先提交代码，再创建标签：

```powershell
git add -A
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\privacy-check.ps1
git diff --cached
git commit -m "release: publish 21世纪内阁 v2.0.0"
git tag -a v2.0.0 -m "21世纪内阁 V2.0"
git push origin main --follow-tags
```

注意：`git add -A` 只能在 `.gitignore` 仍然正确、隐私检查通过且暂存差异经过人工审查后使用。

## 六、交给下一位维护者的验收标准

V2.0 可以发布的前提是：

- 日常使用仍只在两个 `data/` 目录产生个人数据；
- 从 V1.0 升级后，原有订阅、阅读记录、收藏和札记仍可用；
- 隐私检查通过；
- `git ls-files site/data we-mp-rss/data` 没有输出；
- 从全新克隆仓库可以安装并启动；
- GitHub 上仅包含程序、文档和不含真实用户信息的示例数据；
- V2.0 提交和 `v2.0.0` 标签指向同一份已验收代码。

如任何一项无法确认，先不要推送公开仓库。
