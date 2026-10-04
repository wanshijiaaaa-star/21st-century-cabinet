@echo off
REM PDF压缩工具快速使用脚本

echo ========================================
echo PDF压缩工具
echo ========================================
echo.

REM 检查参数
if "%~1"=="" (
    echo 用法: pdf_compress.bat ^<PDF文件路径^> [质量]
    echo.
    echo 示例:
    echo   pdf_compress.bat document.pdf
    echo   pdf_compress.bat document.pdf 70
    echo.
    echo 质量范围: 1-100 ^(默认60^)
    exit /b 1
)

REM 设置质量参数
set quality=60
if not "%~2"=="" set quality=%~2

REM 执行压缩
echo 正在压缩: %~1
echo 图片质量: %quality%
echo.

python "%~dp0pdf_compressor.py" "%~1" -m aggressive -q %quality% -v

echo.
echo ========================================
echo 压缩完成!
echo ========================================
