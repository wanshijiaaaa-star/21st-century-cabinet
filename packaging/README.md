# Windows 独立发行版打包

此目录只面向维护者。普通用户不需要运行这里的脚本，也不需要安装开发环境。

## 架构

发行版由四部分组成：

- `CenturyCabinet.exe`：WinForms 图形启动器，静默启动主站与公众号采集器；
- `Runtime/`：应用私有的 Python 3.13 运行时与依赖，不注册到系统；
- `CenturyCabinet-Setup-<版本>.exe`：包含全部离线负载的每用户安装程序；
- `Uninstall-CenturyCabinet.exe`：随安装程序写入用户选择的程序目录，并注册到 Windows。

程序默认进入 `%LOCALAPPDATA%\Programs\CenturyCabinet`，用户也可选择其他安装目录。个人数据固定进入 `%LOCALAPPDATA%\CenturyCabinet\Data`。升级只替换程序目录。卸载默认只移除程序，除非用户明确勾选删除个人数据。

## 构建

打包机需要 Windows、Python 3.13、已装好 `we-mp-rss/requirements.txt` 的依赖，以及系统自带的 .NET Framework C# 编译器。构建不会把这些要求转嫁给发行版用户。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build-release.ps1
```

依赖不在默认旧版虚拟环境时，可显式指定：

```powershell
.\packaging\build-release.ps1 `
  -PythonHome 'C:\Python313' `
  -SitePackages 'C:\build\cabinet-deps\Lib\site-packages'
```

输出位于仓库根目录的 `release/v<版本>/`，该目录被 Git 忽略。每次构建只清空自己的 `packaging/.build/` 和对应版本的输出目录，不会读取或复制 `site/data/`、`we-mp-rss/data/`。

## 发布前检查

1. 在干净的 Windows 10/11 用户账户运行安装程序；
2. 确认首次启动只出现密码图形窗口，没有终端；
3. 确认桌面和开始菜单入口可启动主站与采集器；
4. 新建一条测试订阅并重启，确认数据仍在；
5. 覆盖安装，确认数据仍在；
6. 默认卸载后重装，确认数据仍在；
7. 勾选删除个人数据卸载，确认数据目录被清理；
8. 检查负载 ZIP 中的 `CenturyCabinet.exe`、`Uninstall-CenturyCabinet.exe` 和运行文件名无乱码；
9. 在空文件夹和已有旧版目录分别测试自定义安装路径、覆盖更新、迁移和卸载；
10. 核对 `SHA256SUMS.txt` 后再上传 GitHub Releases。
