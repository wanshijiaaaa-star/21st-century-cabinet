#!/bin/sh
set -eu

: "${SINGBOX_INBOUND_PORT:=7890}"
: "${SINGBOX_LOG_LEVEL:=info}"
PROXY_URL="${PROXY_URL:-}"

write_direct_config() {
  cat > /tmp/sing-box.json <<EOF
{
  "log": {
    "level": "${SINGBOX_LOG_LEVEL}",
    "timestamp": true
  },
  "inbounds": [
    {
      "type": "mixed",
      "listen": "0.0.0.0",
      "listen_port": ${SINGBOX_INBOUND_PORT},
      "tag": "mixed-in"
    }
  ],
  "outbounds": [
    {
      "type": "direct",
      "tag": "direct"
    }
  ],
  "route": {
    "final": "direct"
  }
}
EOF
}

write_proxy_config() {
  scheme="${PROXY_URL%%://*}"
  rest="${PROXY_URL#*://}"

  username=""
  password=""
  hostport="$rest"
  if printf '%s' "$rest" | grep -q '@'; then
    auth="${rest%@*}"
    hostport="${rest#*@}"
    username="${auth%%:*}"
    password="${auth#*:}"
  fi

  host="${hostport%:*}"
  port="${hostport##*:}"

  case "$scheme" in
    socks|socks5)
      outbound_type="socks"
      version_line='      "version": "5",'
      ;;
    http|https)
      outbound_type="http"
      version_line=''
      ;;
    *)
      echo "unsupported proxy scheme: $scheme" >&2
      exit 1
      ;;
  esac

  cat > /tmp/sing-box.json <<EOF
{
  "log": {
    "level": "${SINGBOX_LOG_LEVEL}",
    "timestamp": true
  },
  "inbounds": [
    {
      "type": "mixed",
      "listen": "0.0.0.0",
      "listen_port": ${SINGBOX_INBOUND_PORT},
      "tag": "mixed-in"
    }
  ],
  "outbounds": [
    {
      "type": "${outbound_type}",
      "tag": "proxy",
      "server": "${host}",
      "server_port": ${port},
EOF

  if [ -n "$version_line" ]; then
    printf '%s\n' "$version_line" >> /tmp/sing-box.json
  fi
  if [ -n "$username" ]; then
    printf '      "username": "%s",\n' "$username" >> /tmp/sing-box.json
  fi
  if [ -n "$password" ]; then
    printf '      "password": "%s",\n' "$password" >> /tmp/sing-box.json
  fi

  cat >> /tmp/sing-box.json <<EOF
      "tag": "proxy-final"
    }
  ],
  "route": {
    "final": "proxy-final"
  }
}
EOF
}

if [ -z "$PROXY_URL" ]; then
  write_direct_config
else
  write_proxy_config
fi

exec sing-box run -c /tmp/sing-box.json
