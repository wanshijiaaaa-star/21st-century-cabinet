# 支持多架构构建
FROM --platform=$BUILDPLATFORM ubuntu:22.04

# 声明构建参数
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG TARGETARCH

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
ENV DEBIAN_FRONTEND=noninteractive

# 安装基础依赖
RUN apt update && apt install -y wget build-essential zlib1g-dev  tzdata git\ 
    libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# 根据架构选择合适的编译参数
RUN if [ "$TARGETARCH" = "arm64" ]; then \
        export CONFIGURE_OPTS="--enable-optimizations --build=aarch64-linux-gnu"; \
    else \
        export CONFIGURE_OPTS="--enable-optimizations"; \
    fi && \
    wget https://mirrors.huaweicloud.com/python/3.13.1/Python-3.13.1.tar.xz && \
    tar -xf Python-3.13.1.tar.xz && \
    cd Python-3.13.1 && \
    ./configure $CONFIGURE_OPTS && \
    make -j$(nproc) && \
    make altinstall && \
    cd .. && \
    rm -rf Python-3.13.1.tar.xz Python-3.13.1

# 创建符号链接
RUN ln -s /usr/local/bin/python3.13 /usr/local/bin/python3 \
    && ln -s /usr/local/bin/pip3.13 /usr/local/bin/pip3

# 自动设置时区（如上海）
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
