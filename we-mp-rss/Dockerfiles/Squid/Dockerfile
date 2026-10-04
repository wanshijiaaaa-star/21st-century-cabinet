# 基于 Alpine Linux 的 Squid HTTPS 代理镜像
FROM alpine:latest

# 安装 Squid 代理服务器、HTTPS 依赖及管理界面工具
RUN apk add --no-cache squid openssl lighttpd \
    && mkdir -p /var/cache/squid \
    && chown -R squid:squid /var/cache/squid \
    && ln -s /usr/lib/squid/cachemgr.cgi /var/www/localhost/cgi-bin/

# 配置 Squid 支持 HTTPS 代理
COPY squid.conf /etc/squid/squid.conf

# 暴露代理端口
EXPOSE 3128

# 启动 Squid 服务
CMD ["squid", "-N"]