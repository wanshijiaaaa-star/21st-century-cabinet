@echo off
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup-windows.ps1"
if errorlevel 1 (
  echo.
  echo 安装失败，请保留本窗口中的错误信息。
  pause
  exit /b 1
)
echo.
echo 安装完成。现在可以启动公众号采集器和21世纪内阁。
pause
