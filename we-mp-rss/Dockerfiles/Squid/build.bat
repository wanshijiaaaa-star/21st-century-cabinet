@echo off
@chcp 65001
REM 设置镜像名称和标签
set IMAGE_NAME=squid-https-proxy
set TAG=latest

REM 切换到当前脚本所在目录
cd /d %~dp0

REM 构建 Docker 镜像
echo 正在构建 Docker 镜像 %IMAGE_NAME%:%TAG% ...
docker build -t %IMAGE_NAME%:%TAG% .

REM 检查构建是否成功
if %errorlevel% neq 0 (
    echo 构建失败，请检查错误信息。
    pause
    exit /b 1
)

echo 镜像构建成功！
echo 镜像名称: %IMAGE_NAME%:%TAG%

REM 可选：推送镜像到 Docker Hub
set /p PUSH="是否推送镜像到 Docker Hub？(y/n): "
if /i "%PUSH%"=="y" (
    echo 正在推送镜像...
    docker push %IMAGE_NAME%:%TAG%
    if %errorlevel% neq 0 (
        echo 推送失败，请检查错误信息。
        pause
        exit /b 1
    )
    echo 镜像推送成功！
)

pause