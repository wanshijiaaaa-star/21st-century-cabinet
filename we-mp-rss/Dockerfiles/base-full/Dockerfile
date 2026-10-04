
FROM  --platform=$BUILDPLATFORM ghcr.io/rachelos/base-mini:latest as werss-base
#

ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
# ENV PIP_INDEX_URL=https://mirrors.huaweicloud.com/repository/pypi/simple

# 复制Python依赖文件
FROM werss-base
# 安装系统依赖
WORKDIR /app
# 复制后端代码
COPY ./requirements.txt ./requirements.txt
COPY ./install.sh  ./install.sh
ENV INSTALL=True BROWSER_TYPE=webkit PLANT_PATH=/app/env/
RUN chmod +x ./install.sh
RUN ./install.sh