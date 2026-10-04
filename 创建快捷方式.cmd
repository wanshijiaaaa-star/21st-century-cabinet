@echo off
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install-shortcuts.ps1"
if errorlevel 1 (
  echo.
  echo 创建快捷方式失败，请保留本窗口中的错误信息。
  pause
  exit /b 1
)
echo.
echo 快捷方式创建完成。
pause
