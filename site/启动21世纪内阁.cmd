@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set "CABINET_PYTHON=%LOCALAPPDATA%\CenturyCabinet\we-rss-venv\Scripts\python.exe"
if not exist "%CABINET_PYTHON%" (
  echo 尚未安装本机环境。请先双击项目根目录的“安装环境.cmd”。
  pause
  exit /b 1
)
"%CABINET_PYTHON%" local_server.py
if errorlevel 1 (
  echo.
  echo 启动失败。请保留本窗口中的错误信息。
  pause
)
