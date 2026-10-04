"""
Async WX Article Fetcher - 完全异步版本
"""
import random
import time
import base64
import re
import os
import asyncio
from html import unescape as html_unescape
from datetime import datetime
from typing import Dict
from bs4 import BeautifulSoup

from .playwright_driver import PlaywrightController
from core.print import print_error, print_info, print_success, print_warning
from core.config import cfg


class WXArticleFetcher:
    """
    异步微信公众号文章获取器
    
    完全基于 async/await,与 FastAPI 完美兼容
    """
    
    def __init__(self, wait_timeout: int = 10000):
        """初始化文章获取器"""
        self.wait_timeout = wait_timeout
        self.controller = PlaywrightController()
        self.browser_proxy_url = ""
        
        if cfg.get("proxy.enabled", False):
            self.browser_proxy_url = cfg.get("proxy.http_url", "")

    async def Close(self):
        """关闭浏览器（异步）"""
        if self.controller:
            await self.controller.Close()

    async def get_article_content(self, url: str) -> Dict:
        """
        获取文章内容(异步)

        Args:
            url: 文章URL

        Returns:
            文章信息字典，包含:
            - id: 文章ID
            - title: 标题
            - author: 作者
            - description: 描述
            - topic_image: 题图
            - publish_time: 发布时间戳
            - content: 正文HTML
            - mp_info: 公众号信息 {mp_name, logo, biz}
            - mp_id: 公众号ID
            - article_type: 文章类型 (0=图文, 5=视频, 7=音频, 10=贴图)
            - fetch_error: 错误信息
        """
        info = {
            "id": self.extract_id_from_url(url),
            "title": "",
            "author": "",
            "description": "",
            "topic_image": "",
            "publish_time": 0,
            "content": "",
            "mp_info": {
                "mp_name": "",
                "logo": "",
                "biz": ""
            },
            "mp_id": "",
            "article_type": 0,  # 默认为图文类型
            "fetch_error": ""
        }

        try:
            # 使用异步上下文管理器
            async with PlaywrightController(
                proxy_url=self.browser_proxy_url,
                mobile_mode=True
            ) as controller:

                # 打开URL
                success = await controller.open_url(url, timeout=self.wait_timeout)
                if not success:
                    raise Exception("页面加载失败")

                page = controller.page

                # 等待页面加载
                await asyncio.sleep(2)

                # 获取页面内容
                body = await page.content()
                body_text = await page.locator("body").text_content()

                # 检查各种异常情况
                if "当前环境异常，完成验证后即可继续访问" in body_text:
                    info["content"] = ""
                    info["fetch_error"] = "当前环境异常，完成验证后即可继续访问"
                    return info

                if "该内容已被发布者删除" in body_text or "The content has been deleted by the author." in body_text:
                    info["content"] = "DELETED"
                    info["fetch_error"] = "该内容已被发布者删除"
                    return info

                if "内容审核中" in body_text:
                    info["content"] = "DELETED"
                    info["fetch_error"] = "内容审核中"
                    return info

                if "该内容暂时无法查看" in body_text:
                    info["content"] = "DELETED"
                    info["fetch_error"] = "该内容暂时无法查看"
                    return info

                if "违规无法查看" in body_text or "Unable to view this content because it violates regulation" in body_text:
                    info["content"] = "DELETED"
                    info["fetch_error"] = "违规无法查看"
                    return info

                if "发送失败无法查看" in body_text:
                    info["content"] = "DELETED"
                    info["fetch_error"] = "发送失败无法查看"
                    return info

                # 获取文章基本信息
                title = await page.locator('meta[property="og:title"]').get_attribute("content")
                author = await page.locator('meta[property="og:article:author"]').get_attribute("content")
                description = await page.locator('meta[property="og:description"]').get_attribute("content")
                topic_image = await page.locator('meta[property="twitter:image"]').get_attribute("content")

                if not title:
                    title = await page.evaluate('() => document.title')

                # 获取发布时间
                publish_time = await self._extract_publish_time(page)

                # 检测文章类型
                article_type = await self._detect_article_type(page)
                info["article_type"] = article_type

                # 获取内容
                content = await page.locator('#js_content').inner_html()
                if not content:
                    content = await page.locator('#js_article').inner_html()

                # 模拟滚动页面到底部，触发懒加载图片
                try:
                    await self._scroll_to_bottom_and_load_images(page)
                except Exception as e:
                    print_warning(f"滚动加载图片失败: {e}")

                # 重新获取内容（滚动后可能有更多图片加载）
                content = await page.locator('#js_content').inner_html()
                if not content:
                    content = await page.locator('#js_article').inner_html()

                content=Web.clean_article_content(str(content))
                # 更新基本信息
                info["title"] = title or ""
                info["author"] = author or ""
                info["description"] = description or ""
                info["topic_image"] = topic_image or ""
                info["publish_time"] = publish_time
                info["content"] = content or ""

                # 获取公众号信息
                try:
                    # 获取公众号头像
                    logo_src = None
                    selectors = [
                        '#js_like_profile_bar .wx_follow_avatar img',
                        '#js_like_profile_bar img.wx_follow_avatar_pic',
                        '.wx_follow_avatar img'
                    ]

                    for selector in selectors:
                        try:
                            ele_logo = page.locator(selector)
                            logo_src = await ele_logo.get_attribute('src', timeout=5000)
                            if logo_src:
                                print_success(f"使用选择器 {selector} 成功获取公众号头像")
                                break
                        except Exception:
                            continue

                    if not logo_src:
                        try:
                            logo_src = await page.locator('meta[property="og:image"]').get_attribute("content", timeout=3000)
                        except Exception:
                            pass

                    # 获取公众号名称
                    mp_name = None
                    try:
                        mp_name = await page.evaluate('() => { const el = document.getElementById("js_wx_follow_nickname"); return el ? el.textContent : null; }')
                    except Exception:
                        pass

                    if not mp_name:
                        mp_name = self._extract_nickname(body or "")

                    if not mp_name:
                        try:
                            mp_name = await page.locator('meta[property="og:article:author"]').get_attribute("content", timeout=3000)
                        except Exception:
                            pass

                    # 获取biz
                    biz = None
                    try:
                        biz = await page.evaluate('() => window.biz')
                    except Exception:
                        pass

                    if not biz:
                        biz = self._extract_biz(url, body or "")

                    info["mp_info"] = {
                        "mp_name": mp_name or "未知公众号",
                        "logo": logo_src or "",
                        "biz": biz or ""
                    }

                    # 生成 mp_id
                    if biz:
                        try:
                            info["mp_id"] = "MP_WXS_" + base64.b64decode(biz).decode("utf-8")
                        except Exception:
                            info["mp_id"] = ""

                except Exception as e:
                    print_error(f"获取公众号信息失败: {str(e)}")
                    info["mp_info"] = {
                        "mp_name": "未知公众号",
                        "logo": "",
                        "biz": ""
                    }
                    info["mp_id"] = ""

                return info

        except Exception as e:
            info["fetch_error"] = str(e)
            print_error(f"获取文章内容失败: {str(e)}")
            return info

    async def _scroll_to_bottom_and_load_images(self, page, scroll_step: int = 500, max_scrolls: int = 50, wait_time: int = 300):
        """
        模拟滚动页面到底部并等待图片加载完成
        
        Args:
            page: Playwright page 对象
            scroll_step: 每次滚动的像素
            max_scrolls: 最大滚动次数
            wait_time: 每次滚动后的等待时间(毫秒)
        """
        try:
            # 获取页面总高度
            total_height = await page.evaluate('() => document.body.scrollHeight')
            current_position = 0
            
            print_info(f"开始滚动加载图片，页面总高度: {total_height}px")
            
            scroll_count = 0
            while current_position < total_height and scroll_count < max_scrolls:
                # 滚动一段距离
                current_position += scroll_step
                await page.evaluate(f'() => window.scrollTo(0, {current_position})')
                
                # 等待图片加载
                await asyncio.sleep(wait_time / 1000)
                
                # 更新页面总高度（可能因为懒加载而变化）
                total_height = await page.evaluate('() => document.body.scrollHeight')
                scroll_count += 1
                
                # 每隔几次滚动输出进度
                if scroll_count % 5 == 0:
                    print_info(f"滚动进度: {current_position}/{total_height}px ({scroll_count}次)")
            
            # 滚动到顶部，然后再到底部确保所有图片加载
            await page.evaluate('() => window.scrollTo(0, 0)')
            await asyncio.sleep(0.5)
            
            # 最后一次性滚动到底部
            await page.evaluate('() => window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(1)
            
            # 等待所有图片加载完成
            await self._wait_for_images_to_load(page)
            
            print_success(f"滚动完成，共滚动 {scroll_count} 次")
            
        except Exception as e:
            print_warning(f"滚动加载图片时出错: {e}")

    async def _wait_for_images_to_load(self, page, timeout: int = 10000):
        """
        等待页面中所有图片加载完成
        
        Args:
            page: Playwright page 对象
            timeout: 超时时间(毫秒)
        """
        try:
            # 使用 JavaScript 检查所有图片是否加载完成
            await page.evaluate('''
                () => {
                    return new Promise((resolve) => {
                        const images = document.querySelectorAll('img');
                        let loaded = 0;
                        const total = images.length;
                        
                        if (total === 0) {
                            resolve();
                            return;
                        }
                        
                        const checkLoaded = () => {
                            loaded++;
                            if (loaded >= total) {
                                resolve();
                            }
                        };
                        
                        images.forEach(img => {
                            if (img.complete) {
                                checkLoaded();
                            } else {
                                img.onload = checkLoaded;
                                img.onerror = checkLoaded;
                            }
                        });
                        
                        // 超时保护
                        setTimeout(resolve, %d);
                    });
                }
            ''' % timeout)
            print_info(f"图片加载等待完成")
        except Exception as e:
            print_warning(f"等待图片加载时出错: {e}")
            
    async def _extract_publish_time(self, page) -> int:
        """
        提取发布时间(异步)
        """
        # 公众号页面并不总是渲染 #publish_time。元素不存在时不能直接
        # 把抓取时刻当成发布时间，否则所有新导入文章都会变成“刚刚”。
        try:
            publish_time_str = await page.locator('#publish_time').text_content(timeout=2000)
            timestamp = self._convert_publish_time_to_timestamp(publish_time_str or "")
            if timestamp:
                return timestamp
        except Exception:
            pass

        try:
            content = await page.content()

            # 微信页面曾使用过 ct、n_time、publish_time、create_time 等变量；
            # 同时兼容 JavaScript 赋值与 JSON 字段。
            patterns = [
                r'["\'](?:ct|n_time|publish_time|create_time|ori_create_time)["\']\s*:\s*["\']?([^"\',;}<]+)',
                r'\b(?:ct|n_time|publish_time|create_time|ori_create_time)\b\s*=\s*["\']?([^"\';,}<]+)',
            ]

            for pattern in patterns:
                for match in re.finditer(pattern, content, flags=re.I):
                    timestamp = self._convert_publish_time_to_timestamp(match.group(1))
                    if timestamp:
                        return timestamp
        except Exception as e:
            print_warning(f"提取发布时间失败: {str(e)}")

        # 0 明确表示未知；调用方不得再替换成抓取时间。
        return 0
            
    async def _detect_article_type(self, page) -> int:
        """
        检测文章类型(异步)
        
        Returns:
            文章类型: 0=图文, 5=视频, 7=音频, 10=贴图
        """
        try:
        
            # 尝试从页面内容中提取
            content = await page.content()
            
           
            
            # 根据页面元素判断类型
            # 检查是否有视频播放器
            has_video = await page.evaluate('() => !!document.querySelector(".video_iframe, #js_video_page_title, [data-vid], mp-common-videosnap")')
            if has_video:
                return 5
            
            # 检查是否有音频播放器
            has_audio = await page.evaluate('() => !!document.querySelector("#js_audio_title, .audio_area, mpvoice")')
            if has_audio:
                return 7
            
            # 检查是否为贴图类型（多图展示）
            has_images = await page.evaluate('() => !!document.querySelector("#js_text_title")')
            if has_images:
                return 10
            

            # 尝试从页面JavaScript变量获取itemShowType
            item_show_type = await page.evaluate('() => window.item_show_type')
            if item_show_type is not None:
                article_type = int(item_show_type)
                # 验证是否为有效类型
                if article_type in [0, 5, 7, 10]:
                    return article_type

             # 查找 itemShowType 的定义
            patterns = [
                r"var\s+itemShowType\s*=\s*window\.a_value_which_never_exists\s*\|\|\s*['\"](\d+)['\"]",
                r"itemShowType\s*=\s*['\"](\d+)['\"]",
                r"item_show_type\s*=\s*['\"](\d+)['\"]",
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    article_type = int(match.group(1))
                    if article_type in [0, 5, 7, 10]:
                        return article_type
            # 默认为图文类型
            return 0
            
        except Exception as e:
            print_warning(f"检测文章类型失败: {str(e)}")
            return 0
            
    def _convert_publish_time_to_timestamp(self, publish_time_str: str) -> int:
        """
        将发布时间字符串转换为时间戳
        支持 "2026年4月9日 22:44" 等中文日期格式（月份/日期可以是单位数）
        """
        try:
            publish_time_str = html_unescape(str(publish_time_str or "")).strip()
            publish_time_str = publish_time_str.strip('"\' ')
            if not publish_time_str:
                return 0

            # 微信脚本中的时间通常是 10 位秒时间戳，也可能是 13 位毫秒。
            if re.fullmatch(r"\d{10,13}", publish_time_str):
                timestamp = int(publish_time_str)
                if timestamp > 10_000_000_000:
                    timestamp //= 1000
                year = datetime.fromtimestamp(timestamp).year
                return timestamp if 2000 <= year <= datetime.now().year + 1 else 0

            # 预处理：补零对齐中文日期中的单位数月份和日期
            # 例如 "2026年4月9日 22:44" -> "2026年04月09日 22:44"
            normalized_str = re.sub(
                r'(\d{4})年(\d{1,2})月(\d{1,2})日',
                lambda m: f"{m.group(1)}年{m.group(2).zfill(2)}月{m.group(3).zfill(2)}日",
                publish_time_str
            )
            
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y年%m月%d日 %H:%M",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d",
                "%Y/%m/%d %H:%M:%S",
                "%Y/%m/%d %H:%M",
                "%Y/%m/%d",
                "%Y年%m月%d日",
                "%m月%d日",
            ]
            
            for fmt in formats:
                try:
                    if fmt == "%m月%d日":
                        current_date = datetime.now()
                        current_year = current_date.year
                        full_time_str = f"{current_year}年{normalized_str}"
                        dt = datetime.strptime(full_time_str, "%Y年%m月%d日")
                        
                        if dt > current_date:
                            dt = dt.replace(year=current_year - 1)
                    else:
                        dt = datetime.strptime(normalized_str, fmt)
                    return int(dt.timestamp())
                except ValueError:
                    continue
                    
            return 0
            
        except Exception as e:
            print_error(f"时间转换失败: {e}")
            return 0
            
    def _extract_biz(self, url: str, content: str) -> str:
        """
        提取 biz 参数
        """
        # 从 URL 提取
        match = re.search(r'[?&]__biz=([^&]+)', url)
        if match:
            return match.group(1)
            
        # 从内容提取
        match = re.search(r'var\s+biz\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)
            
        return ""

    def _extract_nickname(self, content: str) -> str:
        """Extract the publishing account name from WeChat's page script."""
        patterns = (
            r"var\s+nickname\s*=\s*htmlDecode\(\s*([\"'])(.*?)\1\s*\)",
            r"var\s+nickname\s*=\s*([\"'])(.*?)\1",
        )
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if not match:
                continue
            nickname = match.group(2)
            nickname = re.sub(
                r"\\u([0-9a-fA-F]{4})",
                lambda item: chr(int(item.group(1), 16)),
                nickname,
            )
            nickname = re.sub(
                r"\\x([0-9a-fA-F]{2})",
                lambda item: chr(int(item.group(1), 16)),
                nickname,
            )
            nickname = nickname.replace(r"\/", "/").replace(r'\"', '"').replace(r"\'", "'")
            return html_unescape(nickname).strip()
        return ""

    def extract_id_from_url(self, url: str) -> str:
        """从微信文章URL中提取ID
        
        Args:
            url: 文章URL
            
        Returns:
            文章ID字符串，如果提取失败返回空字符串
        """
        try:
            # 从URL中提取ID部分
            match = re.search(r'/s/([A-Za-z0-9_-]+)', url)
            if not match:
                return ""
                
            id_str = match.group(1)
            
            # 添加必要的填充
            padding = 4 - len(id_str) % 4
            if padding != 4:
                id_str += '=' * padding
                
            # 尝试解码base64
            try:
                id_number = base64.b64decode(id_str).decode("utf-8")
                return id_number
            except Exception:
                # 如果base64解码失败，返回原始ID字符串
                return match.group(1)
                
        except Exception as e:
            print_error(f"提取文章ID失败: {e}")
            return ""

    @staticmethod
    def get_description(content: str, length: int = 200) -> str:
        """
        从文章内容中提取描述文本
        
        Args:
            content: HTML 内容
            length: 描述文本的最大长度
            
        Returns:
            描述文本
        """
        if not content:
            return ""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            js_content_div = soup
            if js_content_div is None:
                return ""
            text = js_content_div.get_text().strip().strip("\n").replace("\n", " ").replace("\r", " ")
            return text[:length] + "..." if len(text) > length else text
        except Exception:
            return ""


# Web 工具类(兼容旧代码)
class Web:
    """Web 工具类,提供文章内容清理等功能"""
    @staticmethod
    def fix_images(content:str)->str:
            try:
                soup = BeautifulSoup(content, 'html.parser')
                # 找到内容
                js_content_div = soup
                # 移除style属性中的visibility: hidden;
                if js_content_div is None:
                    return ""
                js_content_div.attrs.pop('style', None)

               

                # 1. 处理img标签，只保留src和style属性
                img_tags = js_content_div.find_all('img')
                for img_tag in img_tags:
                    # 保存需要保留的属性
                    src_value = img_tag.get('src') or img_tag.get('data-src', '')
                    if "data:image" in src_value and src_value!=img_tag.get('data-src','') :
                        src_value = img_tag.get('data-src', '')
                    style_value = img_tag.get('style', '')

                    # 清除所有属性
                    img_tag.attrs = {}

                    # 只设置src和style属性
                    if src_value:
                        img_tag['src'] = src_value
                    if style_value:
                        img_tag['style'] = style_value

                # 2. 处理section、p、span标签，只保留style属性
                for tag_name in ['section', 'p', 'span']:
                    tags = js_content_div.find_all(tag_name)
                    for tag in tags:
                        style_value = tag.get('style', '')
                        # 清除所有属性
                        tag.attrs = {}
                        # 只保留style属性
                        if style_value:
                            tag['style'] = style_value

              

                # 3. 处理背景类资源 (background-image, background等)
                # 查找所有带有style属性的元素
                all_elements = js_content_div.find_all(attrs={'style': True})

                for element in all_elements:
                    style = element.get('style', '')
                    if not style:
                        continue

                    original_style = style

                    # 处理 background-image: url("data-src") 或 background-image: url(data-src)
                    # 微信文章中常见格式: background-image: url("https://mmbiz.qpic.cn/...")
                    # 或使用 data-src 属性值作为占位符
                    def process_bg_url(style_str):
                        """处理背景URL，将data-src属性引用转为实际URL"""
                        # 匹配 url() 中的内容
                        url_pattern = r'url\s*\(\s*["\']?([^"\')\s]+)["\']?\s*\)'

                        def replace_url(match):
                            url_value = match.group(1)
                            # 如果URL是data-src属性引用（如 "data-src" 字符串），尝试从元素获取实际值
                            # 注意：微信文章通常直接使用URL，这里处理边缘情况
                            return match.group(0)

                        return re.sub(url_pattern, replace_url, style_str, flags=re.IGNORECASE)

                    # 检查元素是否有data-src属性，如果有则将其用于背景
                    data_src_value = element.get('data-src', '')
                    if data_src_value and ('background' in style.lower() or 'background-image' in style.lower()):
                        # 如果style中有background但URL为空或无效，用data-src替换
                        # 匹配空的url()或需要替换的情况
                        if 'url()' in style or 'url("")' in style or "url('')" in style:
                            style = re.sub(
                                r'url\s*\(\s*["\']?\s*["\']?\s*\)',
                                f'url("{data_src_value}")',
                                style,
                                flags=re.IGNORECASE
                            )

                    # 更新style属性
                    if style != original_style:
                        element['style'] = style

                # 3. 处理data-src属性在其他元素上的情况
                # 某些元素可能直接使用data-src作为属性（如section、div等）
                elements_with_data_src = js_content_div.find_all(attrs={'data-src': True})
                for element in elements_with_data_src:
                    if element.name != 'img':  # img标签已经处理过了
                        data_src = element.get('data-src', '')
                        if data_src:
                            # 检查style是否有background相关属性
                            style = element.get('style', '')
                            if style and 'background' in style.lower():
                                # 如果有background但没有有效的URL，添加data-src
                                if 'url(' not in style.lower():
                                    # 在style末尾添加background-image
                                    if style.endswith(';'):
                                        element['style'] = f"{style}background-image: url(\"{data_src}\")"
                                    else:
                                        element['style'] = f"{style};background-image: url(\"{data_src}\")"

                section_tags = js_content_div.find_all('section')
                for section in section_tags:
                    section['powered-by'] = 'werss'
                return  js_content_div.prettify()
            except Exception as e:
                print_error(f"修复图片失败: {str(e)}")
            return content
    def clean_article_content(html_content: str,mp_id:str=""):
        from tools.htmltools import htmltools
        html_content=Web.fix_images(html_content)
        # 应用过滤规则
        try:
            from apis.filter_rule import apply_filter_rules
            print(f"[DB] 准备应用过滤规则: mp_id={mp_id}, content_html存在={html_content is not None}")
            if html_content:
                html_content = apply_filter_rules(html_content, mp_id)

        except Exception as e:
            print_warning(f"应用过滤规则失败: {e}")
        if not cfg.get("gather.clean_html",False):
            return html_content
        
        return htmltools.clean_html(str(html_content).strip(),
                                remove_ids=
                                ['content_bottom_interaction',
                                 'activity-name',
                                 'meta_content',
                                 "js_article_bottom_bar",
                                 "js_pc_weapp_code",
                                 "js_novel_card",
                                 "js_pc_qr_code"
                                 ],
                                 remove_selectors=[
                                     "link",
                                     "head",
                                     "script"
                                 ],
                                 remove_attributes=[
                                     {"name":"style","value":"display: none;"},
                                     {"name":"style","value":"display:none;"},
                                     {"name":"aria-hidden","value":"true"},
                                 ],
                                 remove_normal_tag=True
                                 )

    @staticmethod
    def get_article_content(url: str) -> Dict:
        """
        获取文章内容(同步包装器,兼容旧代码)

        注意: 这是一个同步包装器,会阻塞调用线程
        建议使用 WXArticleFetcher().get_article_content() 的 async 版本

        Args:
            url: 文章URL

        Returns:
            文章信息字典
        """
        import asyncio

        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # 创建 fetcher 实例
                fetcher = WXArticleFetcher()

                # 运行异步方法
                result = loop.run_until_complete(fetcher.get_article_content(url))

                return result
            finally:
                # 清理事件循环
                loop.close()

        except Exception as e:
            print_error(f"获取文章内容失败: {e}")
            return {}

    @staticmethod
    def get_description(content:str,length:int=200)->str:
        # 防御性检查：确保 content 不是 None
        if not content:
            return ""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            # 找到内容
            js_content_div = soup
            if js_content_div is None:
                return ""
            text = js_content_div.get_text().strip().strip("\n").replace("\n"," ").replace("\r"," ")
            return text[:length]+"..." if len(text)>length else text
        except Exception:
            return ""

    @staticmethod
    def get_image_url(content: str) -> str:
        """
        从内容中提取图片URL

        Args:
            content: HTML 内容或直接的图片URL

        Returns:
            图片URL
        """
        if not content:
            return ""

        # 如果传入的已经是URL，直接返回
        if content.startswith(('http://', 'https://')):
            return content

        try:
            # 使用 BeautifulSoup 解析
            soup = BeautifulSoup(content, 'html.parser')

            # 查找第一个图片标签
            img = soup.find('img')

            if img:
                # 获取 src 属性
                src = img.get('src') or img.get('data-src')
                if src:
                    return src

            return ""

        except Exception as e:
            print_error(f"提取图片URL失败: {e}")
            return content

    @staticmethod
    def proxy_images(content: str,isProxy:bool=True) -> str:
        """
        处理文章内容中的图片链接，将微信图片转换为代理URL
        
        微信公众号文章图片特点：
        1. 使用 data-src 属性（懒加载）
        2. URL 来自 mmbiz.qpic.cn 等微信 CDN
        3. 可能需要正确的 referer 才能访问
        4. 背景图片使用 CSS background-image 或 background 属性
        
        Args:
            content: HTML 内容
            
        Returns:
            处理后的 HTML 内容
        """
        if not content:
            return content
            
        try:
            soup = BeautifulSoup(content, 'html.parser')
            from urllib.parse import quote
            
            # 处理所有图片标签
            for img in soup.find_all('img'):
                # 获取图片URL（优先 data-src，其次 src）
                img_url = img.get('data-src') or img.get('src')
                
                if img_url and img_url.startswith(('http://', 'https://')):
                    # 将图片URL转换为代理URL
                    encoded_url = quote(img_url, safe='')
                    
                    proxy_url = f"/static/res/logo/{encoded_url}"
                    
                    # 设置 src 属性（确保图片能显示）
                    img['src'] = proxy_url if isProxy else img_url
                    
                    # 如果有 data-src，也更新它
                    if img.has_attr('data-src'):
                        img['data-src'] = proxy_url
                    
                    # 移除可能阻止图片加载的属性
                    for attr in ['data-type', 'data-ratio', 'data-w']:
                        if img.has_attr(attr):
                            del img[attr]
            
            # 处理所有带有 style 属性的元素（背景图片）
            for element in soup.find_all(attrs={'style': True}):
                style = element.get('style', '')
                if not style:
                    continue
                
                # 匹配 background-image: url(...) 或 background: url(...)
                # 支持单引号、双引号和无引号的 URL
                bg_pattern = r'(background-image\s*:\s*url\(|background\s*:[^;]*url\()([\'"]?)(https?://[^\'")\s]+)([\'"]?)\)'
                
                def replace_bg_url(match):
                    prefix = match.group(1)  # background-image: url( 或 background: ... url(
                    quote1 = match.group(2)  # 开始引号
                    img_url = match.group(3)  # 图片 URL
                    quote2 = match.group(4)  # 结束引号
                    
                    # 转换为代理 URL
                    encoded_url = quote(img_url, safe='')
                    proxy_url = f"/static/res/logo/{encoded_url}" if isProxy else img_url
                    
                    return f"{prefix}{quote1}{proxy_url}{quote2})"
                
                new_style = re.sub(bg_pattern, replace_bg_url, style)
                
                if new_style != style:
                    element['style'] = new_style
            
            return str(soup)
            
        except Exception as e:
            print_error(f"处理图片失败: {e}")
            return content


# 导入 asyncio(用于文件顶部)
import asyncio
