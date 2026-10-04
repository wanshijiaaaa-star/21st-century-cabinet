@echo off
chcp 65001 >nul
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-collector.ps1"
if errorlevel 1 (
  echo.
  echo 公众号采集器启动失败。请保留本窗口中的错误信息。
  pause
)
