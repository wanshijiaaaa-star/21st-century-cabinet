from datetime import datetime
def _to_unix_seconds(value) -> int:
    now_ts = int(datetime.now().timestamp())
    if value is None:
        return now_ts
    if isinstance(value, datetime):
        return int(value.timestamp())
    if isinstance(value, (int, float)):
        iv = int(value)
        return int(iv / 1000) if iv > 1_000_000_000_000 else iv
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return now_ts
        if raw.isdigit():
            return _to_unix_seconds(int(raw))
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return int(datetime.strptime(raw, fmt).timestamp())
            except ValueError:
                continue
        try:
            return int(datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp())
        except ValueError:
            return now_ts
    return now_ts
def _to_unix_millis(value, fallback_seconds) -> float:
    now_ts = datetime.now().timestamp()  # 保留小数精度
        # 确保 fallback_seconds 是有效的秒级时间戳
    if fallback_seconds is None:
        fallback_seconds = now_ts
    if isinstance(fallback_seconds, (int, float)):
        if fallback_seconds > 1_000_000_000_000:
            fallback_seconds = fallback_seconds / 1000
        # 不转换为int，保留小数部分
    else:
        fallback_seconds = now_ts

    if value is None:
        return fallback_seconds * 1000
    if isinstance(value, datetime):
        return int(value.timestamp() * 1000)
    if isinstance(value, (int, float)):
        iv = int(value)
        return iv if iv > 1_000_000_000_000 else iv * 1000
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return fallback_seconds * 1000
        if raw.isdigit():
            return _to_unix_millis(int(raw), fallback_seconds)
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return int(datetime.strptime(raw, fmt).timestamp() * 1000)
            except ValueError:
                continue
        try:
            return int(datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp() * 1000)
        except ValueError:
            return fallback_seconds * 1000
    return fallback_seconds * 1000