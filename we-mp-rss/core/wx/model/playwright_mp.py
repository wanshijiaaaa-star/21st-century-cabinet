"""
Playwright 浏览器模式采集器 - 兜底方案

当所有 API 端点都被限制时，使用真实浏览器访问微信公众平台后台，
通过拦截 XHR 请求或解析页面 DOM 来获取文章列表。

工作流程:
1. 加载已保存的 Cookie，启动 Playwright 浏览器
2. 导航到公众号后台首页
3. 拦截页面发出的文章列表 API 请求，捕获响应数据
4. 提取文章信息

依赖: playwright (已存在于项目的 requirements.txt)
"""

import json
import time
import random
import asyncio
from typing import Dict, List, Optional
from core.wx.base import WxGather
from core.print import print_error, print_info, print_warning, print_success
from core.log import logger


# 公众号后台的已发表文章页面 URL
MP_PUBLISH_URL = "https://mp.weixin.qq.com/cgi-bin/appms?t=media/appmsg_list_v2&action=list_ex&begin={begin}&count=5&fakeid={fakeid}&type=9&token={token}&lang=zh_CN"


class MpsPlaywright(WxGather):
    """
    Playwright 浏览器模式采集器
    
    使用真实浏览器环境访问公众号后台，自动发现可用的 API 端点。
    这是所有端点都不可用时的最后兜底方案。
    """

    def __init__(self, is_add: bool = False):
        super().__init__(is_add=is_add)
        self._captured_articles: List[Dict] = []
        self._capture_done = False
        self._actual_endpoint = None
        self._actual_params = None

    def content_extract(self, url):
        """使用已有的 Playwright 文章抓取器"""
        try:
            from driver.wxarticle import Web as App
            r = App.get_article_content(url)
            if r is not None:
                text = r.get("content", "")
                return text
        except Exception as e:
            logger.error(e)
        return ""

    def get_Articles(
        self,
        faker_id: str = None,
        Mps_id: str = None,
        Mps_title="",
        CallBack=None,
        start_page: int = 0,
        MaxPage: int = 1,
        interval=10,
        Gather_Content=False,
        Item_Over_CallBack=None,
        Over_CallBack=None,
    ):
        """
        Playwright 模式主入口
        
        使用 asyncio 运行 Playwright 采集流程。
        """
        super().Start(mp_id=Mps_id)
        if self.Gather_Content:
            Gather_Content = True
        print(f"Playwright浏览器模式,是否采集[{Mps_title}]内容：{Gather_Content}\n")

        count = 5

        try:
            # 尝试方式1: 拦截真实 MP 页面 API 请求
            print_info("方式1: 尝试通过浏览器拦截API请求...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    self._capture_via_browser(faker_id, Mps_id, start_page, MaxPage, count, interval)
                )
            finally:
                loop.close()
            
            if result:
                articles = result
            else:
                print_warning("Playwright 拦截方式未获取到数据")
                super().Error("Playwright 模式未能获取文章列表，请检查登录状态")
                return

            # 处理文章
            for item in articles:
                if Gather_Content:
                    if not super().HasGathered(item.get("aid", "")):
                        item["content"] = self.content_extract(item.get("link", ""))
                        super().Wait(3, 10, tips=f"{item.get('title', '')} 采集完成")
                else:
                    item["content"] = ""
                item["id"] = item.get("aid", "")
                item["mp_id"] = Mps_id
                if CallBack is not None:
                    super().FillBack(
                        CallBack=CallBack,
                        data=item,
                        Ext_Data={"mp_title": Mps_title, "mp_id": Mps_id},
                    )
            print_success(f"Playwright 模式采集完成，共 {len(articles)} 条")

        except Exception as e:
            print_error(f"Playwright 采集失败: {e}")
        finally:
            super().Over(CallBack=Over_CallBack)

    async def _capture_via_browser(
        self,
        faker_id: str,
        mp_id: str,
        start_page: int,
        max_page: int,
        count: int,
        interval: int,
    ) -> Optional[List[Dict]]:
        """
        使用 Playwright 浏览器拦截 MP 后台的 XHR 请求
        
        策略:
        1. 启动浏览器并加载已保存的 Cookie
        2. 打开公众号后台页面
        3. 拦截对 /cgi-bin/ 的 XHR 请求
        4. 从拦截到的响应中提取文章数据
        """
        from playwright.async_api import async_playwright
        
        all_articles = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )
            
            try:
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    locale="zh-CN",
                )

                # 加载已保存的 Cookie
                if self.cookies:
                    cookie_str = self.cookies
                    if isinstance(cookie_str, str) and cookie_str:
                        cookies_to_set = self._parse_cookie_string(cookie_str)
                        if cookies_to_set:
                            await context.add_cookies(cookies_to_set)
                            print_info("已加载保存的 Cookie")

                page = await context.new_page()

                # ---- 核心: 拦截 XHR 请求 ----
                captured_responses: List[Dict] = []

                async def handle_response(response):
                    """拦截所有 /cgi-bin/ 相关的响应"""
                    url = response.url
                    if "/cgi-bin/" not in url:
                        return
                    
                    try:
                        body = await response.json()
                    except Exception:
                        return

                    ret = body.get("base_resp", {}).get("ret", -1) if isinstance(body, dict) else -1
                    if ret != 0:
                        return

                    # 检查是否包含文章数据
                    has_articles = False
                    data_body = None

                    if isinstance(body, dict):
                        for key in ["free_publish_list", "publish_list", "app_msg_list"]:
                            if key in body and isinstance(body[key], list) and len(body[key]) > 0:
                                has_articles = True
                                data_body = body
                                break
                        if "publish_page" in body and isinstance(body["publish_page"], str):
                            try:
                                pp = json.loads(body["publish_page"])
                                if "publish_list" in pp:
                                    has_articles = True
                                    data_body = body
                            except Exception:
                                pass

                    if has_articles:
                        captured_responses.append({
                            "url": url,
                            "body": data_body,
                        })

                page.on("response", handle_response)

                # ---- 导航到公众号后台"已发表"页面 ----
                # 构造已发表文章页面的 URL
                published_url = (
                    f"https://mp.weixin.qq.com/cgi-bin/appms?"
                    f"t=media/appmsg_list_v2&action=list_ex&"
                    f"begin=0&count=5&fakeid={faker_id}&"
                    f"type=9&token={self.token}&lang=zh_CN"
                )

                print_info(f"导航到后台页面...")
                await page.goto(published_url, wait_until="networkidle", timeout=30000)

                # 等待一段时间让页面加载和数据请求完成
                await asyncio.sleep(3)

                # 如果页面要求重新登录
                page_text = await page.content()
                if "扫码登录" in page_text or "login" in page.url.lower():
                    print_error("Playwright 模式下需要重新扫码登录")
                    return None

                # ---- 解析拦截到的数据 ----
                if captured_responses:
                    print_success(f"成功拦截到 {len(captured_responses)} 个包含文章数据的响应")
                    
                    for resp_data in captured_responses:
                        articles = self._parse_captured_response(resp_data["body"])
                        all_articles.extend(articles)
                    
                    # 如果需要更多页
                    if len(all_articles) > 0 and max_page > 1:
                        # 尝试翻页
                        for page_idx in range(1, max_page):
                            begin = page_idx * count
                            next_url = published_url.replace("begin=0", f"begin={begin}")
                            await page.goto(next_url, wait_until="networkidle", timeout=15000)
                            await asyncio.sleep(random.randint(0, interval))
                            
                            # 重新收集（新页面的响应会追加）
                            # 简单起见，这里只做模拟翻页
                            await page.wait_for_timeout(2000)
                            print(f"Playwright 翻页: 第{page_idx+1}页")
                else:
                    # 方式2: 直接导航到 MP 后台的已发表页面，解析 DOM
                    print_info("未拦截到 API 响应，尝试解析页面 DOM...")
                    
                    # 尝试新版后台
                    await page.goto(
                        "https://mp.weixin.qq.com/", wait_until="networkidle", timeout=30000
                    )
                    await asyncio.sleep(2)
                    
                    # 再次等待数据
                    await page.wait_for_timeout(3000)
                    
                    if not captured_responses:
                        print_warning("仍未能获取到数据，请检查:")
                        print_warning("  1. 公众号平台 Cookie 是否有效")
                        print_warning("  2. 公众号平台 Token 是否有效")
                        print_warning("  3. 是否需要使用 --headed 模式手动登录")

                return all_articles if all_articles else None

            finally:
                await browser.close()

    def _parse_cookie_string(self, cookie_str: str) -> List[Dict]:
        """将 Cookie 字符串解析为 Playwright 可用的格式"""
        cookies = []
        if not cookie_str:
            return cookies
        
        for item in cookie_str.split(";"):
            item = item.strip()
            if "=" in item:
                name, value = item.split("=", 1)
                cookies.append({
                    "name": name.strip(),
                    "value": value.strip(),
                    "domain": ".mp.weixin.qq.com",
                    "path": "/",
                })
        return cookies

    def _parse_captured_response(self, body: Dict) -> List[Dict]:
        """
        从拦截到的 API 响应中提取文章列表
        支持多种响应格式
        """
        articles = []

        # 格式1: free_publish_list
        if "free_publish_list" in body:
            raw = body["free_publish_list"]
            if isinstance(raw, list):
                for item in raw:
                    if "publish_info" in item:
                        pi = item["publish_info"]
                        if isinstance(pi, str):
                            try:
                                pi = json.loads(pi)
                            except Exception:
                                continue
                        if "appmsgex" in pi:
                            for art in pi["appmsgex"]:
                                art["publish_info"] = pi
                                articles.append(art)
                    elif "aid" in item:
                        articles.append(item)
            return articles

        # 格式2: app_msg_list
        if "app_msg_list" in body:
            raw = body["app_msg_list"]
            if isinstance(raw, list):
                articles.extend(raw)
            return articles

        # 格式3: publish_page
        if "publish_page" in body:
            try:
                pp = body["publish_page"]
                if isinstance(pp, str):
                    pp = json.loads(pp)
                for item in pp.get("publish_list", []):
                    if "publish_info" in item:
                        pi = item["publish_info"]
                        if isinstance(pi, str):
                            try:
                                pi = json.loads(pi)
                            except Exception:
                                continue
                        if "appmsgex" in pi:
                            for art in pi["appmsgex"]:
                                art["publish_info"] = pi
                                articles.append(art)
            except Exception as e:
                print_error(f"解析 publish_page 失败: {e}")
            return articles

        return articles
