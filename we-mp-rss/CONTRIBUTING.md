# 贡献指南

感谢您考虑对 `we-mp-rss` 项目做出贡献！以下是帮助您开始的一些步骤和建议。

## 如何参与？

1. **查看问题列表**：在 [Issues](https://github.com/rachelos/we-mp-rss/issues) 页面查找适合您的任务。
2. **提出新功能或改进**：如果您有新的想法，请先提交一个 Issue 描述您的计划。
3. **修复已知问题**：选择一个感兴趣的 issue 并尝试解决它。

## 开发环境设置

1. **克隆仓库**
```
bash
git clone https://github.com/rachelos/we-mp-rss.git
cd we-mp-rss
```

2. **安装依赖**
- 如果项目使用 npm：
  ```bash
  npm install
  ```
- 如果项目使用 yarn：
  ```bash
  yarn install
  ```

3. **配置开发环境**
- 复制 `.env.example` 文件并重命名为 `.env`，然后根据需要进行配置。
  ```bash
  cp .env.example .env
  ```
- 编辑 `.env` 文件以包含必要的 API 密钥和其他配置信息。

4. **启动开发服务器**
- 使用微信开发者工具打开项目目录，并点击“预览”按钮。
- 如果有特定的命令用于本地调试，请参考项目 README 中的说明。

## 提交代码

1. **创建分支**
```bash
git checkout -b feature/your-feature-name
```
2. **编写代码并提交更改**
```
git add .
git commit -m "Add your detailed commit message here"
```

3. **推送更改**
```
git push origin feature/your-feature-name
```
4. ***创建 Pull Request***
访问 GitHub 上的仓库页面。
点击“Compare & pull request”按钮。
填写 PR 描述，并请求审查。

## 编码规范
遵循现有的编码风格。
每个提交应保持逻辑单一。
在适当的地方添加注释以提高代码可读性。
请遵循以下命名约定：
文件名：小写字母，单词之间用连字符分隔（例如：rss-parser.js）。
函数名和变量名：驼峰命名法（例如：parseRssFeed）
## 社区准则
尊重所有参与者的意见。
避免任何形式的骚扰或歧视行为。
参与讨论时保持礼貌和尊重。
我们期待您的宝贵贡献！
