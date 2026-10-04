# 请别再加前端编译了，前端编译非常占用工作流时间 ,可以 编译后复制到static目录再提交pull request
FROM --platform=$BUILDPLATFORM ghcr.io/rachelos/base-full:latest AS runtime

ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV INSTALL=True
ENV BROWSER_TYPE=webkit
ENV PLANT_PATH=/app/env
ENV WEREAD_LIC_PATH=/app/data/wx.lic
ENV WEREAD_PROFILE_DIR=/app/data/weread-chrome-profile
ENV PLAYWRIGHT_BROWSERS_PATH=/app/env/driver/_x86_64

WORKDIR /app
RUN echo "1.0.$(date +%Y%m%d.%H%M)">>docker_version.txt
COPY requirements.txt install.sh ./
RUN apt-get update && apt-get install -y --no-install-recommends bash && rm -rf /var/lib/apt/lists/* \
    && chmod +x /app/install.sh && /app/install.sh

COPY . .
COPY config.example.yaml /app/config.yaml
# 微信读书 Cookie 自动刷新：安装 Chromium 浏览器（与 webkit 共存）
RUN VENV=$(ls -d /app/env_* | head -1) && \
    PLAYWRIGHT_BROWSERS_PATH=/app/env/driver/_$(uname -m) "$VENV/bin/python3" -m playwright install chromium && \
    "$VENV/bin/python3" -m playwright install-deps chromium || true
RUN chmod +x /app/start.sh

EXPOSE 8001
CMD ["/app/start.sh"]
