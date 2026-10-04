#!/usr/bin/env python3
"""从齐云代理网站获取免费代理IP"""

import socket
import requests
import re
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed


BASE_URL = "https://www.qiyunip.com/freeProxy/{}.html"
TEST_URLS = [
    "http://ip.sb",       # 简单的IP查询服务
    "http://httpbin.org/ip",
]
TIMEOUT = 8


def check_proxy_tcp(proxy: str) -> tuple:
    """使用socket检测代理TCP连接是否可达
    
    Args:
        proxy: 代理地址 ip:port
        
    Returns:
        tuple: (proxy, is_valid, response_time)
    """
    try:
        ip, port = proxy.split(":")
        port = int(port)
        
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        result = sock.connect_ex((ip, port))
        response_time = time.time() - start_time
        sock.close()
        
        if result == 0:
            return (proxy, True, response_time, "tcp_ok")
    except Exception as e:
        return (proxy, False, 0, f"tcp_error: {str(e)[:30]}")
    
    return (proxy, False, 0, "tcp_refused")


def check_proxy_http(proxy: str) -> tuple:
    """使用HTTP请求检测代理是否可用
    
    Args:
        proxy: 代理地址 ip:port
        
    Returns:
        tuple: (proxy, is_valid, response_time, error_msg)
    """
    proxies = {
        "http": f"http://{proxy}",
        "https": f"http://{proxy}"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
    }
    
    for test_url in TEST_URLS:
        start_time = time.time()
        try:
            response = requests.get(
                test_url, 
                proxies=proxies, 
                headers=headers,
                timeout=TIMEOUT,
                allow_redirects=True
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                return (proxy, True, response_time, "http_ok")
        except requests.exceptions.ProxyError as e:
            return (proxy, False, 0, f"proxy_error")
        except requests.exceptions.ConnectTimeout:
            return (proxy, False, 0, f"timeout")
        except requests.exceptions.ReadTimeout:
            return (proxy, False, 0, f"read_timeout")
        except Exception as e:
            continue
    
    return (proxy, False, 0, "http_failed")


def check_proxy(proxy: str, use_tcp: bool = True) -> tuple:
    """检测单个代理是否可用
    
    Args:
        proxy: 代理地址 ip:port
        use_tcp: 是否先用TCP检测
        
    Returns:
        tuple: (proxy, is_valid, response_time)
    """
    # 先用TCP检测，快速过滤不可达的
    if use_tcp:
        _, tcp_valid, tcp_time, tcp_msg = check_proxy_tcp(proxy)
        if not tcp_valid:
            return (proxy, False, 0)
    
    # TCP可达，再用HTTP检测
    _, http_valid, http_time, http_msg = check_proxy_http(proxy)
    return (proxy, http_valid, http_time)


def verify_proxies(proxies: list, workers: int = 20, debug: bool = False) -> list:
    """批量检测代理可用性
    
    Args:
        proxies: 代理列表
        workers: 并发线程数
        debug: 是否显示详细错误
        
    Returns:
        list: 可用的代理列表
    """
    valid_proxies = []
    total = len(proxies)
    checked = 0
    
    print(f"\n开始检测代理可用性（并发数: {workers}）...")
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(check_proxy, p): p for p in proxies}
        
        for future in as_completed(futures):
            checked += 1
            proxy, is_valid, response_time = future.result()
            
            if is_valid:
                valid_proxies.append((proxy, response_time))
                print(f"  [{checked}/{total}] ✓ {proxy} ({response_time:.2f}s)")
            else:
                if debug:
                    print(f"  [{checked}/{total}] ✗ {proxy}")
    
    print(f"\n检测结果: {len(valid_proxies)}/{total} 可用")
    
    # 按响应时间排序
    valid_proxies.sort(key=lambda x: x[1])
    
    return [p[0] for p in valid_proxies]


def fetch_page(page: int) -> list:
    """获取单页代理IP
    
    Args:
        page: 页码
        
    Returns:
        list: 代理列表
    """
    url = BASE_URL.format(page)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = "utf-8"
        html = response.text
    except Exception as e:
        print(f"  第{page}页请求失败: {e}")
        return []
    
    # 使用正则提取IP和端口
    pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*(\d{2,5})'
    matches = re.findall(pattern, html)
    
    proxies = []
    for ip, port in matches:
        proxy = f"{ip}:{port}"
        if proxy not in proxies:
            proxies.append(proxy)
    
    return proxies


def fetch_proxies(pages: int = 1) -> list:
    """获取多页代理IP
    
    Args:
        pages: 要抓取的页数
        
    Returns:
        list: 代理列表，格式为 ["ip:port", ...]
    """
    all_proxies = []
    
    for page in range(1, pages + 1):
        print(f"正在获取第 {page}/{pages} 页...")
        proxies = fetch_page(page)
        
        for proxy in proxies:
            if proxy not in all_proxies:
                all_proxies.append(proxy)
        
        print(f"  获取到 {len(proxies)} 个，累计 {len(all_proxies)} 个")
        
        # 页间延迟，避免请求过快
        if page < pages:
            time.sleep(1)
    
    return all_proxies


def save_proxies(proxies: list, output_path: str = "data/proxy.txt"):
    """保存代理到文件
    
    Args:
        proxies: 代理列表
        output_path: 输出文件路径
    """
    # 确保目录存在
    output_file = Path(output_path)
    if not output_file.is_absolute():
        # 相对路径则基于脚本所在目录的上级目录
        script_dir = Path(__file__).parent.parent
        output_file = script_dir / output_path
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        for proxy in proxies:
            f.write(proxy + "\n")
    
    print(f"已保存 {len(proxies)} 个代理到 {output_file}")


def main():
    parser = argparse.ArgumentParser(description="从齐云代理网站获取免费代理IP")
    parser.add_argument("-p", "--pages", type=int, default=1, help="抓取页数，默认1页")
    parser.add_argument("-o", "--output", type=str, default="data/proxy.txt", help="输出文件路径")
    parser.add_argument("-w", "--workers", type=int, default=20, help="检测并发数，默认20")
    parser.add_argument("--no-check", action="store_true", help="跳过可用性检测")
    parser.add_argument("--debug", action="store_true", help="显示详细检测信息")
    args = parser.parse_args()
    
    print(f"开始抓取 {args.pages} 页代理IP...")
    proxies = fetch_proxies(args.pages)
    
    if not proxies:
        print("未获取到代理IP")
        return
    
    print(f"\n原始获取到 {len(proxies)} 个代理")
    
    # 检测可用性
    if not args.no_check:
        proxies = verify_proxies(proxies, args.workers, args.debug)
    
    if proxies:
        print(f"\n有效代理 {len(proxies)} 个:")
        for i, proxy in enumerate(proxies[:10], 1):
            print(f"  {i}. {proxy}")
        if len(proxies) > 10:
            print(f"  ... 还有 {len(proxies) - 10} 个")
        
        save_proxies(proxies, args.output)
    else:
        print("没有可用的代理IP")
        print("\n提示: 免费代理可用率通常只有1-5%，建议增加抓取页数:")
        print("  python tools/fetch_proxy.py -p 10")


if __name__ == "__main__":
    main()
