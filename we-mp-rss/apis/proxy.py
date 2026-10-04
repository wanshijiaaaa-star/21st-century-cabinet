"""
代理服务模块 - 用于突破 iframe 跨域限制
"""
from fastapi import APIRouter, Request, Response
import httpx
from urllib.parse import urlparse, urljoin, quote
import logging
import re
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/proxy", tags=["代理服务"])

# 允许代理的域名白名单（安全加固：只允许微信公众号相关域名）
ALLOWED_DOMAINS = ['mp.weixin.qq.com', 'weixin.qq.com', 'www.wesoso.com']

# 资源处理的标签和属性映射
RESOURCE_TAGS = {
    'a': ['href'],
    'img': ['src', 'srcset', 'data-src'],
    'script': ['src'],
    'link': ['href'],
    'iframe': ['src'],
    'video': ['src', 'poster'],
    'audio': ['src'],
    'source': ['src'],
    'track': ['src'],
    'embed': ['src'],
    'object': ['data'],
    'form': ['action'],
    'input': ['src'],
    'frame': ['src'],
}


def get_base_directory(url: str) -> str:
    """
    获取 URL 的基础目录
    
    Args:
        url: 完整 URL
        
    Returns:
        str: 基础目录 URL
    """
    try:
        parsed = urlparse(url)
        # 去掉查询参数和片段
        path = parsed.path
        # 如果有路径，获取目录部分
        if path and '/' in path:
            path = path.rsplit('/', 1)[0]
        else:
            path = ''
        
        base_dir = f"{parsed.scheme}://{parsed.netloc}{path}/"
        return base_dir
    except Exception as e:
        logger.error(f"获取基础目录失败: {str(e)}")
        return url


def rewrite_relative_urls(content: str, base_url: str) -> str:
    """
    重写 HTML 内容中的相对 URL 为绝对 URL
    
    Args:
        content: HTML 内容
        base_url: 基础 URL
        
    Returns:
        str: 重写后的 HTML 内容
    """
    try:
        # 获取基础目录
        base_dir = get_base_directory(base_url)
        
        logger.info(f"原始 URL: {base_url}")
        logger.info(f"基础目录: {base_dir}")
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # 处理各种标签中的 URL
        for tag_name, attrs in RESOURCE_TAGS.items():
            for tag in soup.find_all(tag_name):
                for attr in attrs:
                    if tag.has_attr(attr):
                        original_url = str(tag[attr])
                        
                        # 跳过不需要处理的 URL
                        if not original_url or original_url.startswith(('data:', 'mailto:', 'tel:', 'javascript:', '#')):
                            continue
                        
                        logger.debug(f"处理 {tag_name}.{attr}: {original_url}")
                        
                        # 转换为绝对 URL
                        absolute_url = urljoin(base_dir, original_url)
                        
                        # 代理化 URL（需要 URL 编码）
                        encoded_url = quote(absolute_url, safe='')
                        proxy_url = f"/proxy/proxy?url={encoded_url}"
                        
                        logger.info(f"重写: {original_url} -> {proxy_url}")
                        tag[attr] = proxy_url
        
        # 处理 srcset 属性（特殊格式）
        for tag in soup.find_all(['img', 'source']):
            if tag.has_attr('srcset'):
                srcset = str(tag['srcset'])
                urls = []
                for part in srcset.split(','):
                    part = part.strip()
                    if part:
                        # 提取 URL 和描述符
                        parts = part.split()
                        url_part = parts[0]
                        descriptor = ' '.join(parts[1:]) if len(parts) > 1 else ''
                        
                        if url_part and not url_part.startswith(('http://', 'https://', 'data:')):
                            absolute_url = urljoin(base_dir, url_part)
                            encoded_url = quote(absolute_url, safe='')
                            proxy_url = f"/proxy/proxy?url={encoded_url}"
                            
                            if descriptor:
                                urls.append(f"{proxy_url} {descriptor}")
                            else:
                                urls.append(proxy_url)
                            logger.info(f"重写 srcset: {url_part} -> {proxy_url}")
                        else:
                            urls.append(part)
                
                tag['srcset'] = ', '.join(urls)
        
        # 处理 style 属性中的 url()
        for tag in soup.find_all(attrs={'style': True}):
            style = str(tag['style'])
            tag['style'] = rewrite_css_urls(style, base_dir)
        
        # 处理内联 CSS
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                style_tag.string = rewrite_css_urls(str(style_tag.string), base_dir)
        
        # 添加或更新 base 标签
        base_tag = soup.find('base')
        if not base_tag:
            head = soup.find('head')
            if head:
                new_base = soup.new_tag('base', href=base_dir)
                head.insert(0, new_base)
                logger.info(f"添加 base 标签: {base_dir}")
        else:
            base_tag['href'] = base_dir
            logger.info(f"更新 base 标签: {base_dir}")
        
        return str(soup)
    except Exception as e:
        logger.error(f"重写 URL 失败: {str(e)}", exc_info=True)
        return content


def rewrite_css_urls(css_content: str, base_url: str) -> str:
    """
    重写 CSS 内容中的 url() 引用
    
    Args:
        css_content: CSS 内容
        base_url: 基础 URL
        
    Returns:
        str: 重写后的 CSS 内容
    """
    try:
        # 匹配 url() 中的 URL
        pattern = r'url\(["\']?([^)"\']+)["\']?\)'
        
        def replace_url(match):
            url = match.group(1)
            if url and not url.startswith(('http://', 'https://', 'data:', 'about:')):
                absolute_url = urljoin(base_url, url)
                encoded_url = quote(absolute_url, safe='')
                proxy_url = f"/proxy/proxy?url={encoded_url}"
                return f'url("{proxy_url}")'
            return match.group(0)
        
        return re.sub(pattern, replace_url, css_content)
    except Exception as e:
        logger.error(f"重写 CSS URL 失败: {str(e)}")
        return css_content

def is_domain_allowed(url: str) -> bool:
    """
    检查域名是否在允许列表中（安全加固：增加协议和内网IP检查）

    Args:
        url: 目标URL

    Returns:
        bool: 是否允许代理
    """
    if ALLOWED_DOMAINS is None:
        return False  # 安全加固：默认拒绝而非允许

    try:
        parsed = urlparse(url)

        # 1. 只允许http/https协议
        if parsed.scheme not in ['http', 'https']:
            logger.warning(f"拒绝非HTTP(S)协议: {parsed.scheme}")
            return False

        # 2. 禁止访问内网IP和特殊IP
        import ipaddress
        import socket

        hostname = parsed.hostname
        if hostname:
            try:
                # 尝试解析域名
                ip_str = socket.gethostbyname(hostname)
                ip = ipaddress.ip_address(ip_str)

                # 禁止私有IP、回环IP、链路本地IP
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    logger.warning(f"拒绝内网IP访问: {hostname} -> {ip}")
                    return False
            except (socket.gaierror, ValueError):
                # 域名解析失败或不是IP，继续检查域名白名单
                pass

        # 3. 检查域名白名单
        domain = parsed.netloc
        # 移除端口号
        domain = domain.split(':')[0]

        if domain not in ALLOWED_DOMAINS:
            logger.warning(f"域名不在白名单中: {domain}")
            return False

        return True

    except Exception as e:
        logger.error(f"域名检查异常: {str(e)}")
        return False


@router.get("/{path:path}")
async def proxy_get_request(path: str, request: Request):
    """
    代理 GET 请求
    
    代理外部 URL 的请求，解决 iframe 跨域限制
    
    Args:
        path: 代理的路径
        request: FastAPI 请求对象
        
    Returns:
        Response: 代理的响应内容
    """
    # 从查询参数中获取目标 URL
    target_url = request.query_params.get("url")
    
    logger.info(f"收到代理请求: {target_url}")
    
    if not target_url:
        return Response(
            content="Missing 'url' parameter",
            status_code=400,
            media_type="text/plain"
        )
    
    # 检查域名白名单
    if not is_domain_allowed(target_url):
        logger.warning(f"尝试代理不允许的域名: {target_url}")
        return Response(
            content="Domain not allowed",
            status_code=403,
            media_type="text/plain"
        )
    
    try:
        # 获取客户端请求头
        headers = dict(request.headers)
        
        # 移除不应该转发的头
        headers.pop('host', None)
        headers.pop('content-length', None)
        headers.pop('content-encoding', None)
        headers.pop('transfer-encoding', None)
        
        # 添加用户代理（避免被反爬虫拦截）
        headers['User-Agent'] = headers.get('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # 获取查询参数（除了 url 参数）
        query_params = dict(request.query_params)
        query_params.pop('url', None)
        
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
            verify=True  # 安全加固：启用SSL证书验证
        ) as client:
            # 发起代理请求
            response = await client.get(
                target_url,
                headers=headers,
                params=query_params if query_params else None
            )
            
            # 构建响应
            content = response.content
            content_type = response.headers.get('content-type', 'text/html')
            
            logger.info(f"代理请求: {target_url}")
            logger.info(f"响应类型: {content_type}")
            
            # 处理 HTML 内容 - 重写相对路径
            if 'html' in content_type.lower():
                try:
                    # 解码内容
                    encoding = response.encoding or 'utf-8'
                    html_content = content.decode(encoding, errors='ignore')
                    
                    # 重写相对 URL
                    html_content = rewrite_relative_urls(html_content, target_url)
                    
                    # 重新编码
                    content = html_content.encode(encoding)
                    logger.info("HTML 内容处理完成")
                except Exception as e:
                    logger.error(f"处理 HTML 内容失败: {str(e)}", exc_info=True)
            
            # 处理 CSS 内容
            elif 'css' in content_type.lower():
                try:
                    base_dir = get_base_directory(target_url)
                    encoding = response.encoding or 'utf-8'
                    css_content = content.decode(encoding, errors='ignore')
                    
                    # 重写 CSS 中的 url()
                    css_content = rewrite_css_urls(css_content, base_dir)
                    
                    content = css_content.encode(encoding)
                    logger.info("CSS 内容处理完成")
                except Exception as e:
                    logger.error(f"处理 CSS 内容失败: {str(e)}", exc_info=True)
            
            response_headers = dict(response.headers)
            
            # 移除不应该返回的头
            response_headers.pop('content-encoding', None)
            response_headers.pop('transfer-encoding', None)
            response_headers.pop('content-length', None)
            
            # 添加 CORS 相关头
            response_headers['Access-Control-Allow-Origin'] = '*'
            response_headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response_headers['Access-Control-Allow-Headers'] = '*'
            
            # 针对微信公众号文章的特殊处理
            # 添加一些安全相关的头，允许在 iframe 中显示
            response_headers['X-Frame-Options'] = 'ALLOWALL'
            response_headers['Content-Security-Policy'] = "frame-ancestors *"
            
            return Response(
                content=content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=content_type
            )
            
    except httpx.TimeoutException:
        logger.error(f"代理请求超时: {target_url}")
        return Response(
            content="Request timeout",
            status_code=504,
            media_type="text/plain"
        )
    except Exception as e:
        logger.error(f"代理请求失败: {target_url}, 错误: {str(e)}")
        return Response(
            content=f"Proxy error: {str(e)}",
            status_code=500,
            media_type="text/plain"
        )


@router.options("/{path:path}")
async def proxy_options_request(path: str, request: Request):
    """
    处理 OPTIONS 请求（CORS 预检请求）
    """
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': '*',
        'Access-Control-Max-Age': '86400',
    }
    return Response(headers=headers, status_code=200)


@router.post("/{path:path}")
async def proxy_post_request(path: str, request: Request):
    """
    代理 POST 请求
    
    Args:
        path: 代理的路径
        request: FastAPI 请求对象
        
    Returns:
        Response: 代理的响应内容
    """
    # 从查询参数中获取目标 URL
    target_url = request.query_params.get("url")
    
    if not target_url:
        return Response(
            content="Missing 'url' parameter",
            status_code=400,
            media_type="text/plain"
        )
    
    # 检查域名白名单
    if not is_domain_allowed(target_url):
        logger.warning(f"尝试代理不允许的域名: {target_url}")
        return Response(
            content="Domain not allowed",
            status_code=403,
            media_type="text/plain"
        )
    
    try:
        # 获取请求体
        body = await request.body()
        
        # 获取客户端请求头
        headers = dict(request.headers)
        
        # 移除不应该转发的头
        headers.pop('host', None)
        headers.pop('content-length', None)
        headers.pop('content-encoding', None)
        headers.pop('transfer-encoding', None)
        
        # 添加用户代理
        headers['User-Agent'] = headers.get('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # 获取查询参数（除了 url 参数）
        query_params = dict(request.query_params)
        query_params.pop('url', None)
        
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
            verify=True  # 安全加固：启用SSL证书验证
        ) as client:
            # 发起代理请求
            response = await client.post(
                target_url,
                content=body,
                headers=headers,
                params=query_params if query_params else None
            )
            
            # 构建响应
            content = response.content
            response_headers = dict(response.headers)
            
            # 移除不应该返回的头
            response_headers.pop('content-encoding', None)
            response_headers.pop('transfer-encoding', None)
            response_headers.pop('content-length', None)
            
            # 添加 CORS 相关头
            response_headers['Access-Control-Allow-Origin'] = '*'
            response_headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response_headers['Access-Control-Allow-Headers'] = '*'
            
            return Response(
                content=content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get('content-type', 'text/html')
            )
            
    except httpx.TimeoutException:
        logger.error(f"代理请求超时: {target_url}")
        return Response(
            content="Request timeout",
            status_code=504,
            media_type="text/plain"
        )
    except Exception as e:
        logger.error(f"代理请求失败: {target_url}, 错误: {str(e)}")
        return Response(
            content=f"Proxy error: {str(e)}",
            status_code=500,
            media_type="text/plain"
        )
