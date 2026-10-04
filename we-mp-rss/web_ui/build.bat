@echo off

:: 设置路径变量
set DIST_DIR="dist"
set TARGET_DIR="..\static"
:: 执行构建
call yarn build

:: 复制文件到static目录
echo 正在复制构建文件到%TARGET_DIR%...
rmdir /s /q %TARGET_DIR%
if not exist %TARGET_DIR% mkdir %TARGET_DIR%
xcopy "%DIST_DIR%\*" "%TARGET_DIR%" /E /Y /I