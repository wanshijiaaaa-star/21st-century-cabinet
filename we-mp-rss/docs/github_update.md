# GitHub 更新功能使用说明

本项目新增了从 GitHub 自动更新源码的功能，支持通过 API 接口和命令行工具两种方式使用。

## 功能特性

- ✅ 自动检查 Git 仓库状态
- ✅ 安全的代码更新（支持备份）
- ✅ 提交历史查看
- ✅ 分支管理
- ✅ 代码回滚功能
- ✅ RESTful API 接口
- ✅ 命令行工具

## API 接口使用

### 1. 检查 Git 状态

```bash
GET /api/github/status
```

**参数:**
- `path` (可选): 仓库路径

**响应示例:**
```json
{
  "is_git_repo": true,
  "current_branch": "main",
  "has_changes": false,
  "remote_url": "https://github.com/rachelos/we-mp-rss.git",
  "last_commit": "abc1234 Fix some bugs",
  "ahead_commits": 0,
  "behind_commits": 2,
  "error": null
}
```

### 2. 更新代码

```bash
POST /api/github/update
```

**请求体:**
```json
{
  "branch": "main",        // 可选，目标分支
  "backup": true,           // 可选，是否创建备份
  "path": "/path/to/repo"   // 可选，仓库路径
}
```

**响应示例:**
```json
{
  "success": true,
  "message": "成功更新 5 个文件",
  "backup_created": true,
  "backup_path": "/path/to/backup_20231127_143022",
  "updated_files": ["file1.py", "file2.js"],
  "error": null
}
```

### 3. 获取提交历史

```bash
GET /api/github/commits?limit=10
```

**参数:**
- `limit`: 返回的提交数量 (默认 10，最大 100)
- `path`: 可选的仓库路径

### 4. 获取分支列表

```bash
GET /api/github/branches
```

### 5. 回滚到指定提交

```bash
POST /api/github/rollback
```

**请求体:**
```json
{
  "commit_hash": "abc1234",
  "path": "/path/to/repo"
}
```

## 命令行工具使用

项目根目录提供了 `github_update.py` 脚本，方便命令行操作。

### 基本用法

```bash
# 检查状态
python github_update.py --status

# 更新代码
python github_update.py --update

# 更新到指定分支
python github_update.py --update --branch main

# 更新但不创建备份
python github_update.py --update --no-backup

# 查看提交历史
python github_update.py --history --limit 20

# 查看所有分支
python github_update.py --branches

# 回滚到指定提交
python github_update.py --rollback abc1234

# 以 JSON 格式输出
python github_update.py --status --json
```

### 高级用法

```bash
# 指定仓库路径
python github_update.py --path /path/to/repo --status

# 组合使用
python github_update.py --update --branch develop --backup
```

## 安全特性

### 1. 自动备份
- 默认在更新前创建完整备份
- 备份文件命名格式: `backup_YYYYMMDD_HHMMSS`
- 备份包含完整的 Git 仓库历史

### 2. 状态检查
- 更新前检查是否有未提交的更改
- 验证 Git 仓库状态
- 检查与远程仓库的差异

### 3. 错误处理
- 完善的错误提示
- 操作失败时的回滚机制
- 详细的日志记录

## 注意事项

### ⚠️ 重要提醒

1. **备份重要性**: 建议始终开启备份功能，特别是在生产环境
2. **未提交更改**: 更新前请确保所有更改已提交或暂存
3. **回滚风险**: 回滚操作会永久丢失后续提交，请谨慎使用
4. **网络依赖**: 更新功能需要能够访问 GitHub 仓库

### 🔧 故障排除

**常见问题:**

1. **"不是 Git 仓库"错误**
   - 确保在正确的 Git 仓库目录中执行操作
   - 检查 `.git` 目录是否存在

2. **"存在未提交的更改"错误**
   - 使用 `git status` 查看未提交的文件
   - 提交更改: `git add . && git commit -m "保存更改"`
   - 或暂存更改: `git stash`

3. **网络连接问题**
   - 检查网络连接
   - 确认能够访问 GitHub
   - 检查防火墙设置

4. **权限问题**
   - 确保有足够的文件系统权限
   - 检查仓库目录的读写权限

## 集成到自动化流程

### Cron 定时更新

```bash
# 每天凌晨 2 点自动检查更新
0 2 * * * cd /path/to/we-mp-rss && python github_update.py --status --json > /var/log/github_status.log

# 每周日凌晨 3 点自动更新（带备份）
0 3 * * 0 cd /path/to/we-mp-rss && python github_update.py --update --backup >> /var/log/github_update.log 2>&1
```

### CI/CD 集成

```yaml
# GitHub Actions 示例
- name: Update from upstream
  run: |
    python github_update.py --update --no-backup
    if [ $? -eq 0 ]; then
      echo "Update successful"
      # 触发后续部署流程
    fi
```

## 开发和扩展

### 添加新功能

1. 在 `tools/github_updater.py` 中添加核心功能
2. 在 `apis/github_update.py` 中添加 API 接口
3. 更新命令行工具 `github_update.py`
4. 添加相应的测试用例

### 自定义配置

可以通过修改 `GitHubUpdater` 类来支持:
- 不同的 Git 托管平台 (Gitee, GitLab 等)
- 自定义备份策略
- 特定的分支保护规则
- 集成通知系统

## 技术实现

- **后端**: FastAPI + Python
- **Git 操作**: subprocess 调用 git 命令
- **错误处理**: 完善的异常捕获和用户友好的错误信息
- **安全性**: 输入验证、路径检查、操作确认

## 支持和反馈

如有问题或建议，请通过以下方式联系:
- 提交 Issue 到项目仓库
- 查看项目文档
- 联系开发团队