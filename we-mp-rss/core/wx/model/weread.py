"""
微信读书(Weread)通道采集器

通过微信读书 Web API 采集指定用户的：
- 书架上的书籍列表
- 每本书的划线/笔记（高亮标注）
- 阅读进度和统计信息

API 端点（需要已登录的 Cookie）:
全部走 weread 主站 web 域（https://weread.qq.com/web/...），与
scripts/weread_scan_diag.py 实测成功的路径一致：
- 书架:  https://weread.qq.com/web/shelf/sync?userVid=&synckey=0
        （注意：userVid 必须传空字符串，非空反而会触发 -2012/401！
        参考 steptian/weread-mp 与诊断脚本实测）
- 书籍详情: https://weread.qq.com/web/book/info?bookId={bookId}
- 笔记/划线: https://weread.qq.com/web/book/bookmarklist?bookId={bookId}
- 章节列表: https://weread.qq.com/web/book/chapterInfos?bookIds={bookId}&synckeys=0
- 评论: https://weread.qq.com/web/review/list?bookId={bookId}&listType=11
- 阅读统计: https://weread.qq.com/web/book/readstat?bookId={bookId}

认证方式:
- 需要从浏览器获取 weread.qq.com 的 Cookie
- 关键 Cookie: wr_vid, wr_skey, wr_gid, wr_fp, wr_name
- Cookie 存储在 data/wx.lic 下独立的 weread 区段
"""

import json
import time
import random
from typing import Dict, List, Optional
from core.wx.base import WxGather
from core.print import print_error, print_info, print_warning, print_success
from core.log import logger


# ---- 微信读书 API 配置 ----
# 注意：必须用 weread 主站 web 域！i 域（i.weread.qq.com）对短值 wr_skey /
# 未续期 Cookie 直接返回 HTTP 401；web 域返回 200 + 业务码 -2012，且
# userVid 必须传空字符串（诊断脚本实测：非空反而触发 -2012）。
WEREAD_BASE = "https://weread.qq.com"


class MpsWeread(WxGather):
    """
    微信读书采集器

    将以用户为中心采集：
    1. 书架上的所有书籍
    2. 每本书的笔记/划线（高亮标注）
    3. 阅读进度信息

    每本书映射为 Feed（订阅源），每条笔记/划线映射为 Article（文章）。
    """

    def __init__(self, is_add: bool = False):
        super().__init__(is_add=is_add)
        self._weread_cookies: str = ""
        self._weread_ticket: str = ""
        self._weread_vid: str = ""
        self._weread_name: str = ""

    def _load_weread_auth(self):
        """加载微信读书的 Cookie"""
        from core.config import Config, cfg as app_cfg
        import os

        lic_path = "./data/wx.lic"
        os.makedirs(os.path.dirname(lic_path), exist_ok=True)
        if not os.path.exists(lic_path):
            with open(lic_path, "w") as f:
                f.write("{}")

        weread_cfg = Config(lic_path)
        weread_data = weread_cfg.get("weread_data", {})
        if isinstance(weread_data, str):
            try:
                weread_data = json.loads(weread_data)
            except Exception:
                weread_data = {}

        self._weread_cookies = app_cfg.get("weread.cookie", "") or weread_data.get("cookie", "")
        self._weread_ticket = app_cfg.get("weread.ticket", "") or weread_data.get("ticket", "")
        self._weread_vid = app_cfg.get("weread.vid", "") or weread_data.get("vid", "")
        self._weread_name = weread_data.get("name", "")

    def _weread_get(self, url: str, params: dict = None) -> Optional[dict]:
        """带微信读书 Cookie 的 GET 请求（web 域，浏览器完整请求头）"""
        import requests

        headers = {
            "Cookie": self._weread_cookies,
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Origin": "https://weread.qq.com",
            "Referer": "https://weread.qq.com/",
        }

        try:
            proxies = self._get_proxies()
            resp = requests.get(
                url, params=params, headers=headers, proxies=proxies, timeout=15
            )
            if resp.status_code == 200:
                payload = resp.json()
                # 微信读书以 HTTP 200 返回业务错误（登录态失效等），
                # 必须检查 errcode，否则「登录超时」会被当成空书架（0 本书）
                errcode = payload.get("errCode", payload.get("errcode", 0))
                if errcode in (-2012, -2010, -2041):
                    print_warning(
                        "Weread API 登录态失效: "
                        f"{payload.get('errmsg') or payload.get('errlog') or errcode}"
                        "（Cookie 已过期或无效，请在「微信读书管理」页重新扫码授权）"
                    )
                    return None
                return payload
            elif resp.status_code == 401 or resp.status_code == 403:
                print_warning(
                    f"Weread API 认证失败: {resp.status_code}（Cookie 已过期或无效，"
                    "请在「微信读书管理」页重新扫码授权）"
                )
                return None
            else:
                print_warning(f"Weread API 返回 {resp.status_code}: {url}")
                return None
        except requests.exceptions.Timeout:
            print_warning(f"Weread API 超时: {url}")
            return None
        except Exception as e:
            print_warning(f"Weread API 异常: {e}")
            return None

    def _get_shelf_books(self) -> List[Dict]:
        """获取书架上的所有书籍"""
        if not self._weread_vid:
            print_error("微信读书 vid 未设置，请先在管理页保存 Cookie")
            return []

        url = f"{WEREAD_BASE}/web/shelf/sync"
        params = {
            # 关键：userVid 必须传空字符串！非空反而会触发 -2012「登录超时」，
            # 参考 scripts/weread_scan_diag.py 与 steptian/weread-mp 实测。
            "userVid": "",
            "synckey": 0,
            "lectureSynckey": 0,
        }

        data = self._weread_get(url, params)
        if data is None:
            # 请求失败/登录态失效，返回 None 供调用方区分「失败」与「空书架」
            return None
        if not data:
            return []

        books = []
        # 书架数据格式: {"books": [...], "synckey": xxx}
        raw_books = data.get("books", [])
        for item in raw_books:
            book_id = str(item.get("bookId", ""))
            if not book_id:
                continue
            books.append({
                "book_id": book_id,
                "title": item.get("title", ""),
                "author": item.get("author", ""),
                "cover": item.get("cover", ""),
                "intro": item.get("intro", ""),
                "category": item.get("category", ""),
                "progress": item.get("progress", 0),
                "chapterUid": item.get("chapterUid", 0),
                "update_time": item.get("updateTime", 0),
                "readingTime": item.get("readingTime", 0),
                "finishedDate": item.get("finishedDate", 0),
                "format": item.get("format", ""),
            })
        return books

    def _weread_post(self, url: str, json_data: dict = None, params: dict = None) -> Optional[dict]:
        """带微信读书 Cookie 的 POST 请求（web 域）。

        返回解析后的 JSON dict；HTTP/超时/非 JSON 时返回 None。
        业务错误（errCode != 0）不在此处拦截，交由调用方处理。
        """
        import requests

        headers = {
            "Cookie": self._weread_cookies,
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Origin": "https://weread.qq.com",
            "Referer": "https://weread.qq.com/",
            "Content-Type": "application/json",
        }
        try:
            proxies = self._get_proxies()
            resp = requests.post(
                url, params=params, json=json_data, headers=headers,
                proxies=proxies, timeout=15,
            )
        except requests.exceptions.Timeout:
            print_warning(f"Weread API 超时: {url}")
            return None
        except Exception as e:
            print_warning(f"Weread API 异常: {e}")
            return None
        if resp.status_code != 200:
            print_warning(f"Weread API 返回 {resp.status_code}: {url}")
            return None
        try:
            return resp.json()
        except ValueError:
            print_warning(f"Weread API 响应非 JSON: {url}")
            return None

    def add_to_shelf(self, book_id: str) -> dict:
        """把 bookId 加入微信读书书架。

        公众号在书架上即视为「已关注」。接口: POST /web/shelf/add，
        请求体: {"bookIds": [book_id]}（参考 ylw1997/wereadapi 实测文档）。
        返回微信读书原始 JSON；请求失败时返回 {"errCode": -1, ...}。
        """
        if not book_id:
            return {"errCode": -1, "errMsg": "empty book_id"}
        payload = self._weread_post(
            f"{WEREAD_BASE}/web/shelf/add",
            json_data={"bookIds": [book_id]},
        )
        if payload is None:
            return {"errCode": -1, "errMsg": "request failed"}
        return payload

    def ensure_mp_on_shelf(self, book_id: str, mp_name: str = "") -> tuple:
        """确保公众号在微信读书书架上，不在则自动添加（关注）。

        流程: 拉取书架 -> 若 bookId 已在书架则跳过 -> POST /web/shelf/add。
        返回: (ok: bool, detail: str)，ok=True 表示可正常采集（已在书架或已添加）。
        """
        from core.config import cfg

        name = mp_name or book_id
        if not str(book_id or "").startswith("MP_WXS_"):
            return True, "非微信读书公众号，跳过书架检查"
        if not cfg.get("weread.auto_add_to_shelf", True):
            return True, "未启用自动添加书架（weread.auto_add_to_shelf=false）"
        if not self._weread_vid:
            self._weread_vid = self._extract_vid_from_cookie(self._weread_cookies)

        shelf = self._get_shelf_books()
        if shelf is None:
            # 与「空书架」区分：请求失败/登录态失效
            return False, "书架获取失败（Cookie 可能已过期），无法确认书架状态"
        if any(b["book_id"] == book_id for b in shelf):
            return True, "已在书架"
        if not self._weread_vid:
            return False, "Cookie 中未找到 wr_vid，无法自动添加到书架"

        payload = self.add_to_shelf(book_id)
        if not isinstance(payload, dict):
            return False, f"shelf/add 失败: {payload}"
        code = payload.get("errCode", payload.get("errcode", 0))
        if code == 0:
            return True, f"「{name}」已自动添加到书架"
        if code in (-2012, -2010, -2041):
            return False, f"登录态失效，无法添加书架: {payload.get('errMsg', code)}"
        return False, f"shelf/add 失败: {payload.get('errMsg', payload)} (errCode={code})"

    def _get_book_bookmarks(self, book_id: str) -> List[Dict]:
        """获取一本书的划线/笔记"""
        url = f"{WEREAD_BASE}/web/book/bookmarklist"
        params = {"bookId": book_id}

        data = self._weread_get(url, params)
        if not data:
            return []

        # 笔记数据格式: {"updated": [...], "synckey": xxx}
        bookmarks = data.get("updated", [])
        result = []
        for bm in bookmarks:
            result.append({
                "bookmark_id": bm.get("bookmarkId", ""),
                "chapter_uid": bm.get("chapterUid", 0),
                "chapter_name": bm.get("chapterName", ""),
                "content": bm.get("markText", ""),
                "note": bm.get("content", ""),  # 用户自己的笔记
                "style": bm.get("style", 0),     # 划线样式
                "type": bm.get("type", 0),       # 类型(0=划线,1=其他)
                "create_time": bm.get("createTime", 0),
                "update_time": bm.get("updateTime", 0),
                "range": bm.get("range", ""),
                "color_style": bm.get("colorStyle", 0),
                "book_version": bm.get("bookVersion", 0),
            })
        return result

    def _get_book_info(self, book_id: str) -> Optional[Dict]:
        """获取书籍详情"""
        url = f"{WEREAD_BASE}/web/book/info"
        params = {"bookId": book_id}

        data = self._weread_get(url, params)
        if not data:
            return None

        return {
            "book_id": str(data.get("bookId", book_id)),
            "title": data.get("title", ""),
            "author": data.get("author", ""),
            "cover": data.get("cover", ""),
            "intro": data.get("intro", ""),
            "category": data.get("category", ""),
            "publisher": data.get("publisher", ""),
            "translator": data.get("translator", ""),
            "isbn": data.get("isbn", ""),
            "totalWords": data.get("totalWords", 0),
            "price": data.get("price", 0),
            "originalPrice": data.get("originalPrice", 0),
            "publishTime": data.get("publishTime", ""),
            "rating": data.get("newRating", 0),
            "ratingCount": data.get("newRatingCount", 0),
            "reviewCount": data.get("newReviewCount", 0),
            "type": data.get("type", 0),
        }

    def _get_chapter_info(self, book_id: str) -> List[Dict]:
        """获取书籍章节列表"""
        # 注：web 域无 /web/book/chapterInfos 接口（实测 404），
        # 该接口在主流程中未被调用，失败时静默返回空列表。
        url = f"{WEREAD_BASE}/web/book/chapterInfos"
        params = {"bookIds": book_id, "synckeys": 0}

        data = self._weread_get(url, params)
        if not data or not data.get("data"):
            return []

        chapters = []
        for chapter_data in data["data"]:
            if not chapter_data:
                continue
            updated = chapter_data.get("updated", [])
            for ch in updated:
                chapters.append({
                    "chapter_uid": ch.get("chapterUid", 0),
                    "chapter_idx": ch.get("chapterIdx", 0),
                    "title": ch.get("title", ""),
                    "word_count": ch.get("wordCount", 0),
                    "update_time": ch.get("updateTime", 0),
                    "pay_status": ch.get("payStatus", 0),
                })
        return chapters

    def _extract_vid_from_cookie(self, cookie_str: str) -> str:
        """从 Cookie 字符串中提取 wr_vid"""
        if not cookie_str:
            return ""
        for item in cookie_str.split(";"):
            item = item.strip()
            if item.startswith("wr_vid="):
                return item.replace("wr_vid=", "").strip()
        return ""

    def content_extract(self, url: str) -> str:
        """微信读书暂不需要外部链接内容提取"""
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
        微信读书主入口：采集笔记/划线

        工作流程:
        1. 加载微信读书 Cookie
        2. 通过 faker_id (即 bookId) 直接采集该书的划线/笔记
        3. 如果 faker_id 为空，则遍历所有书架书籍
        4. 每条划线/笔记作为一条 Article 输出
        """
        super().Start(mp_id=Mps_id)
        if self.Gather_Content:
            Gather_Content = True

        # 加载微信读书的认证信息
        self._load_weread_auth()

        if not self._weread_cookies:
            super().Error("微信读书 Cookie 未配置，请在管理页设置", code="Invalid Session")
            return

        # 自动提取 vid
        if not self._weread_vid:
            self._weread_vid = self._extract_vid_from_cookie(self._weread_cookies)

        if not self._weread_vid:
            super().Error("无法从 Cookie 中提取 wr_vid，请检查 Cookie 是否完整")
            return

        print_info(f"微信读书采集模式，用户: {self._weread_name or '未知'}")
        print_info(f"源标识: {Mps_title} (bookId={faker_id})\n")

        all_bookmarks = []

        if faker_id and faker_id.strip():
            if str(faker_id).startswith("MP_WXS_"):
                # 公众号书在微信读书内只有订阅流，没有划线/笔记数据
                print_warning(
                    f"《{Mps_title}》是公众号订阅（{faker_id}），微信读书不支持其划线采集，"
                    "请切换 gather.model=weread_mp 模式采集公众号文章"
                )
                super().Over(CallBack=Over_CallBack)
                return
            # 指定了 bookId，直接采集该书的笔记
            print_info(f"采集书籍 {Mps_title} 的笔记/划线...")
            bookmarks = self._get_book_bookmarks(faker_id)
            for bm in bookmarks:
                bm["book_id"] = faker_id
                bm["book_title"] = Mps_title
            all_bookmarks = bookmarks
            print_info(f"获取到 {len(all_bookmarks)} 条笔记/划线")
        else:
            # 未指定 bookId，遍历书架采集所有书的笔记
            print_info("获取书架书籍列表...")
            books = self._get_shelf_books()
            print_info(f"书架上共 {len(books)} 本书")

            if not books:
                print_warning("书架上没有书籍或获取失败")
                super().Over(CallBack=Over_CallBack)
                return

            for idx, book in enumerate(books):
                book_id = book["book_id"]
                book_title = book["title"]

                if str(book_id).startswith("MP_WXS_"):
                    # 公众号订阅没有划线/笔记数据，跳过以免误报"0 条"
                    print_warning(
                        f"[{idx+1}/{len(books)}] 跳过公众号《{book_title}》"
                        f"（{book_id}）：微信读书不支持公众号划线采集，"
                        "请用 weread_mp 模式采集文章"
                    )
                    continue

                print_info(f"[{idx+1}/{len(books)}] 采集《{book_title}》的笔记...")
                time.sleep(random.randint(1, interval))

                try:
                    bookmarks = self._get_book_bookmarks(book_id)
                    for bm in bookmarks:
                        bm["book_id"] = book_id
                        bm["book_title"] = book_title
                    all_bookmarks.extend(bookmarks)
                    print_info(f"  《{book_title}》: {len(bookmarks)} 条笔记")
                except Exception as e:
                    print_error(f"  《{book_title}》采集失败: {e}")

                print_info(f"已采集 {len(all_bookmarks)} 条笔记")

            print_success(f"全部笔记采集完成，共 {len(all_bookmarks)} 条")

        # 将笔记输出为标准 Article 格式
        for bm in all_bookmarks:
            # 构造文章数据 - 划线内容作为 title，笔记作为 content
            mark_text = bm.get("content", "") or bm.get("markText", "")
            note = bm.get("note", "")
            book_title = bm.get("book_title", Mps_title)
            chapter_name = bm.get("chapter_name", "")

            # 标题: 书中原文摘录（截断显示）
            title = mark_text[:200] if mark_text else f"《{book_title}》笔记"
            if chapter_name:
                title = f"[{chapter_name}] {title}"

            # 正文: 包含完整划线内容和笔记
            content_parts = [f"「{mark_text}」"] if mark_text else []
            if note:
                content_parts.append(f"\n\n>>> 我的笔记:\n{note}")
            content = "\n".join(content_parts)

            item = {
                "aid": bm.get("bookmark_id", "") or str(int(time.time() * 1000)),
                "title": title,
                "link": f"https://weread.qq.com/web/reader/{bm.get('book_id', '')}",
                "cover": "",
                "digest": mark_text[:500] if mark_text else "",
                "content": content,
                "create_time": bm.get("create_time", 0),
                "update_time": bm.get("update_time", 0),
                "item_show_type": 0,
                "copyright_stat": 1,
                # 扩展信息
                "book_id": bm.get("book_id", ""),
                "book_title": book_title,
                "chapter_name": chapter_name,
                "note_text": note,
                "style": bm.get("style", 0),
            }

            item["id"] = item["aid"]
            item["mp_id"] = Mps_id

            if CallBack is not None:
                super().FillBack(
                    CallBack=CallBack,
                    data=item,
                    Ext_Data={"mp_title": Mps_title, "mp_id": Mps_id},
                )

        super().Over(CallBack=Over_CallBack)

    # ---- 辅助方法 ----

    def test_auth(self) -> dict:
        """
        测试微信读书认证是否有效
        返回: {"ok": bool, "name": str, "vid": str, "book_count": int, "error": str}
        """
        self.get_token()  # 加载基础配置
        self._load_weread_auth()

        if not self._weread_cookies:
            return {"ok": False, "name": "", "vid": "", "book_count": 0, "error": "Cookie 未配置"}

        if not self._weread_vid:
            self._weread_vid = self._extract_vid_from_cookie(self._weread_cookies)

        if not self._weread_vid:
            return {"ok": False, "name": "", "vid": "", "book_count": 0, "error": "Cookie 中未找到 wr_vid"}

        books = self._get_shelf_books()
        if books is None:
            return {"ok": False, "name": "", "vid": self._weread_vid, "book_count": 0, "error": "API 请求失败，Cookie 可能已过期"}

        # 尝试获取用户名
        name = self._weread_name
        if not name and books:
            # 从第一本书尝试获取更多信息
            pass

        return {
            "ok": True,
            "name": name,
            "vid": self._weread_vid,
            "book_count": len(books),
            "error": "",
        }
