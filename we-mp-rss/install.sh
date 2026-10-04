#!/bin/bash
plantform="$(uname -m)"
PLANT_PATH=${PLANT_PATH:-/app/env}
plant="${PLANT_PATH}_${plantform}"
python3 -m venv $plant
source $plant/bin/activate
echo "使用虚拟环境: $plant"


# 检查函数：检查包是否已安装
check_package() {
    if command -v "$1" >/dev/null 2>&1; then
        echo "$1 已安装"
        return 0
    elif dpkg -l "$1" 2>/dev/null | grep -q "^ii"; then
        echo "$1 已安装"
        return 0
    else
        echo "$1 未安装"
        return 1
    fi
}
# 检查所有需要的包
packages=("wget" "git" "build-essential" "zlib1g-dev" 
          "libgdbm-dev" "libnss3-dev" "libssl-dev" "libreadline-dev" 
          "libffi-dev" "libsqlite3-dev" "procps" )

# X Server 相关依赖（用于非 headless 浏览器）
if [ "$HEADLESS" != "true" ] || [ "$ENABLE_XVFB" = "true" ]; then
    echo "添加 Xvfb 和 X11 依赖包..."
    packages+=("xvfb" "x11-utils" "libgtk-3-0" "libnotify4" "libnss3" "libxss1" "libxtst6" "libasound2" "libgbm1")
fi

# if [ "$EXPORT_PDF" = "True" ]; then
#     echo "添加libreoffice依赖包..."
#     packages+=("fonts-noto-cjk" "libreoffice")
# fi

echo "检查依赖包安装状态..."
for package in "${packages[@]}"; do
    if ! check_package "$package"; then
        missing_packages+=("$package")
    fi
done
echo "${missing_packages[*]}"
if [ ${#missing_packages[@]} -eq 0 ]; then
    echo "所有依赖都已安装，无需重复安装。"
else
    echo "需要安装的包: ${missing_packages[*]}"
    echo "开始安装..."
    apt update && apt install -y ${missing_packages[*]} --no-install-recommends\
        && rm -rf /var/lib/apt/lists/*
    if [ $? -eq 0 ]; then
        echo "安装完成！"
    else
        echo "安装失败！"
        exit 1
    fi
fi

ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

PLAYWRIGHT_BROWSERS_PATH=${PLAYWRIGHT_BROWSERS_PATH:-${PLANT_PATH}/driver/_${plantform}}
BROWSER_TYPE=${BROWSER_TYPE:-webkit}
echo "export PLAYWRIGHT_BROWSERS_PATH=${PLAYWRIGHT_BROWSERS_PATH}
export TZ=Asia/Shanghai
export BROWSER_TYPE=${BROWSER_TYPE}">/app/environment.sh
echo "环境变量已设置"
chmod +x /app/environment.sh
cat /app/environment.sh
source /app/environment.sh
echo "source /app/environment.sh
source $plant/bin/activate">/etc/profile
# pip3 install --upgrade pip

# 检查requirements.txt更新
if [ -f "requirements.txt" ]; then
    CURRENT_MD5=$(md5sum requirements.txt | cut -d' ' -f1)
    OLD_MD5_FILE="${PLANT_PATH}/requirements.txt.md5"
    
    if [ -f "$OLD_MD5_FILE" ] && [ "$CURRENT_MD5" = "$(cat $OLD_MD5_FILE)" ]; then
        echo "requirements.txt未更新，跳过安装"
    else
        echo "安装requirements.txt依赖..."
        pip3 install -r requirements.txt
        echo $CURRENT_MD5 > $OLD_MD5_FILE
    fi
fi 

INSTALL=${INSTALL:-False}
# 根据环境变量决定是否安装浏览器
if [ "$INSTALL" = True ]; then
    echo "INSTALL环境变量为$INSTALL，开始安装playwright浏览器..."
    playwright install $BROWSER_TYPE --with-deps
else
    echo "INSTALL环境变量为$INSTALL，跳过playwright浏览器安装"
fi
