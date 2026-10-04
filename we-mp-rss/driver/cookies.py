import time
def expire(cookies:any) :
    if not isinstance(cookies, list) and  not isinstance(cookies, dict):
        raise TypeError("cookies参数必须是列表类型")
    
    cookie_expiry=None
    
    # 优先检查的 cookie 名称列表（按优先级排序）
    # slave_sid 是微信公众平台的会话 cookie，但可能不存在或没有 expires
    # 添加更多可能携带有效期的 cookie
    priority_cookies = ['slave_sid', 'slave_user', 'bizuin', 'uin', 'pass_ticket']
    
    # 首先尝试从优先列表中查找
    for priority_name in priority_cookies:
        for cookie in cookies:
            if not isinstance(cookie, dict):
                continue
            if cookie.get('name') == priority_name:
                expiry = _extract_expiry_from_cookie(cookie)
                if expiry:
                    return expiry
    
    # 如果优先列表都没找到，遍历所有 cookie 找有 expires 的
    for cookie in cookies:
        if not isinstance(cookie, dict):
            continue
        expiry = _extract_expiry_from_cookie(cookie)
        if expiry:
            return expiry
    
    # 如果所有 cookie 都没有有效过期时间，返回一个默认值
    # 表示当前会话有效，但不清楚具体过期时间
    # 这样不会导致登录状态被标记为失败
    from core.print import print_warning
    print_warning("未能从 cookies 中提取有效过期时间，使用默认2小时有效期")
    default_expiry = time.time() + 7200  # 默认2小时
    return {
        'expiry_timestamp': default_expiry,
        'remaining_seconds': 7200,
        'expiry_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(default_expiry))
    }

def _extract_expiry_from_cookie(cookie: dict):
    """从单个 cookie 中提取过期时间"""
    # 检查多种可能的过期时间字段名
    expiry_fields = ['expires', 'expiry', 'expire']
    expiry_time = None
    
    for field in expiry_fields:
        if field in cookie:
            try:
                val = cookie[field]
                # 处理不同类型的值
                if isinstance(val, (int, float)):
                    expiry_time = float(val)
                elif isinstance(val, str):
                    # 尝试解析字符串
                    if val.isdigit():
                        expiry_time = float(val)
                    else:
                        # 可能是日期字符串，尝试解析
                        import datetime
                        try:
                            # 尝试常见日期格式
                            for fmt in ['%Y-%m-%d %H:%M:%S', '%a, %d-%b-%Y %H:%M:%S %Z', '%a, %d %b %Y %H:%M:%S %Z']:
                                try:
                                    dt = datetime.datetime.strptime(val, fmt)
                                    expiry_time = dt.timestamp()
                                    break
                                except ValueError:
                                    continue
                        except Exception:
                            pass
                break
            except (ValueError, TypeError) as e:
                continue
    
    if expiry_time:
        remaining_time = expiry_time - time.time()
        if remaining_time > 0:
            return {
                'expiry_timestamp': expiry_time,
                'remaining_seconds': int(remaining_time),
                'expiry_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expiry_time))
            }
    
    return None


