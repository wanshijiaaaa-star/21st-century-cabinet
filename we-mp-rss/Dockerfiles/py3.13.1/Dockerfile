# 使用指定的基础镜像，如果 ARM64 架构拉取失败，请尝试以下解决方案
FROM ghcr.io/rachelos/base:latest

# 设置 pip 镜像源
ENV PIP_INDEX_URL=https://mirrors.huaweicloud.com/repository/pypi/simple

# 更新包管理器并安装必要的依赖
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制 requirements.txt 文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip3 install --no-cache-dir -r requirements.txt -i https://mirrors.huaweicloud.com/repository/pypi/simple

