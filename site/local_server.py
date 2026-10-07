from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sqlite3
import subprocess
import threading
import time
import urllib.error
import urllib.request
import unicodedata
import webbrowser
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse, urlsplit
from uuid import uuid4


ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
DATA = Path(os.environ.get("CENTURY_CABINET_SITE_DATA_DIR", str(ROOT / "data"))).resolve()
DB_PATH = DATA / "cabinet.db"
BACKUP_DIR = DATA / "backups"
COLLECTOR_ROOT = Path(
    os.environ.get("CENTURY_CABINET_COLLECTOR_ROOT", str(ROOT.parent / "we-mp-rss"))
).resolve()
COLLECTOR_DATA = Path(
    os.environ.get("CENTURY_CABINET_COLLECTOR_DATA_DIR", str(COLLECTOR_ROOT / "data"))
).resolve()
COLLECTOR_DB_PATH = COLLECTOR_DATA / "db.db"
COLLECTOR_PYTHON = Path(
    os.environ.get(
        "CENTURY_CABINET_PYTHON",
        str(Path(os.environ.get("LOCALAPPDATA", "")) / "CenturyCabinet" / "we-rss-venv" / "Scripts" / "python.exe"),
    )
).resolve()
COLLECTOR_WORKDIR = Path(
    os.environ.get("CENTURY_CABINET_COLLECTOR_WORKDIR", str(COLLECTOR_ROOT))
).resolve()
COLLECTOR_CONFIG = Path(
    os.environ.get("CENTURY_CABINET_COLLECTOR_CONFIG", str(COLLECTOR_DATA / "config.yaml"))
).resolve()
RELEASE_MODE = os.environ.get("CENTURY_CABINET_RELEASE") == "1"
RETENTION_DAYS = 90
TRASH_RETENTION_DAYS = 7
SYNC_INTERVALS = {"A": 12 * 3600, "B": 24 * 3600, "C": 72 * 3600}
MAX_FEED_BYTES = 8 * 1024 * 1024
MAX_ARTICLE_BYTES = 4 * 1024 * 1024
COLLECTOR_CONTENT_URL = "http://127.0.0.1:8001/api/v1/wx/articles/content/by-url"
COLLECTOR_BASE_URL = "http://127.0.0.1:8001/"
COLLECTOR_ADD_URL = "http://127.0.0.1:8001/add-subscription"
COLLECTOR_SYNC_URL = "http://127.0.0.1:8001/api/v1/wx/task-queue/cabinet/sync-all"
COLLECTOR_SYNC_STATUS_URL = "http://127.0.0.1:8001/api/v1/wx/task-queue/cabinet/status"
COLLECTOR_LAUNCHER = ROOT / "start-collector.ps1"
GITHUB_RELEASES_API = "https://api.github.com/repos/wanshijiaaaa-star/21st-century-cabinet/releases/latest"
GITHUB_RELEASES_URL = "https://github.com/wanshijiaaaa-star/21st-century-cabinet/releases/latest"


def read_current_version() -> str:
    for path in (ROOT.parent / "VERSION", ROOT.parent.parent / "VERSION"):
        try:
            version = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if version:
            return version
    return "1.1.0"


CURRENT_VERSION = read_current_version()


def version_key(value: str) -> tuple[int, int, int]:
    match = re.search(r"\d+(?:\.\d+){1,2}", str(value))
    if not match:
        raise ValueError("版本号格式不正确")
    parts = [int(part) for part in match.group(0).split(".")]
    return tuple((parts + [0, 0, 0])[:3])


def check_for_update() -> dict:
    request = urllib.request.Request(
        GITHUB_RELEASES_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"21st-Century-Cabinet/{CURRENT_VERSION}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == HTTPStatus.NOT_FOUND:
            raise ValueError("GitHub Releases 暂无可用版本") from error
        raise ValueError(f"GitHub 暂时无法响应（{error.code}）") from error
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        raise ValueError("无法连接 GitHub，请检查网络后重试") from error

    if not isinstance(payload, dict):
        raise ValueError("GitHub 返回了无法识别的版本信息")
    tag_name = str(payload.get("tag_name") or "").strip()
    match = re.search(r"\d+(?:\.\d+){1,2}", tag_name)
    if not match:
        raise ValueError("最新发行版缺少有效版本号")
    latest_version = match.group(0)
    release_url = str(payload.get("html_url") or GITHUB_RELEASES_URL).strip()
    allowed_prefix = "https://github.com/wanshijiaaaa-star/21st-century-cabinet/releases/"
    if not release_url.startswith(allowed_prefix):
        release_url = GITHUB_RELEASES_URL
    return {
        "ok": True,
        "currentVersion": CURRENT_VERSION,
        "latestVersion": latest_version,
        "updateAvailable": version_key(latest_version) > version_key(CURRENT_VERSION),
        "releaseUrl": release_url,
        "releaseName": str(payload.get("name") or tag_name).strip(),
        "publishedAt": payload.get("published_at"),
    }


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def normalized_summary_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", clean_text(value))
    return re.sub(r"[\W_]+", "", text, flags=re.UNICODE).casefold()


def is_duplicate_summary(title: str | None, summary: str | None) -> bool:
    normalized_title = normalized_summary_text(title)
    normalized_summary = normalized_summary_text(summary)
    return bool(normalized_title and normalized_title == normalized_summary)


def finalize_summary(value: str | None, length: int = 76) -> str:
    text = clean_text(value)
    if not text:
        return ""
    limit = max(24, int(length))
    sentence_end = re.search(r"[。！？!?]", text[: limit + 1])
    if sentence_end:
        text = text[:sentence_end.end()]
    elif len(text) > limit:
        text = text[:limit]
    text = re.sub(r"[。！？!?；;，,、：:\s…—-]+$", "", text).strip()
    return f"{text}。" if text else ""


def summary_from_text(title: str | None, value: str | None, length: int = 76) -> str:
    text = clean_text(value)
    title_text = clean_text(title)
    if title_text and text.startswith(title_text):
        text = text[len(title_text):].lstrip(" ：:|｜·-—")
    if not text or is_duplicate_summary(title, text):
        return ""
    return finalize_summary(text, length)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":")[-1].lower()


def first_text(node: ET.Element, *names: str) -> str:
    wanted = {name.lower() for name in names}
    for child in node.iter():
        if local_name(child.tag) in wanted and child.text:
            return child.text.strip()
    return ""


def entry_link(node: ET.Element) -> str:
    for child in node.iter():
        if local_name(child.tag) != "link":
            continue
        href = child.attrib.get("href", "").strip()
        rel = child.attrib.get("rel", "alternate")
        if href and rel in ("alternate", ""):
            return href
        if child.text and child.text.strip():
            return child.text.strip()
    return ""


def entry_cover(node: ET.Element, raw: str) -> str:
    for child in node.iter():
        name = local_name(child.tag)
        url = child.attrib.get("url", "").strip()
        media_type = child.attrib.get("type", "")
        if url and (name in {"thumbnail", "content"} or (name == "enclosure" and media_type.startswith("image/"))):
            return url
    match = re.search(r"<img\b[^>]*\bsrc=[\"']([^\"']+)", raw, flags=re.I)
    return match.group(1) if match else ""


def parse_published(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def latest_collector_entries(
    results: list[tuple[str, list[dict], str | None]],
    collector_source_ids: set[str],
) -> list[tuple[str, list[dict], str | None]]:
    """Keep only the newest local publication date from collector RSS results."""
    dated_entries: list[tuple[dict, datetime]] = []
    for source_id, entries, error in results:
        if error or source_id not in collector_source_ids:
            continue
        for entry in entries:
            published = parse_published(str(entry.get("publishedAt") or ""))
            if published:
                dated_entries.append((entry, published.astimezone()))
    if not dated_entries:
        return results

    newest_date = max(published.date() for _, published in dated_entries)
    filtered = []
    for source_id, entries, error in results:
        if source_id in collector_source_ids and not error:
            entries = [
                entry
                for entry in entries
                if (
                    (published := parse_published(str(entry.get("publishedAt") or "")))
                    and published.astimezone().date() == newest_date
                )
            ]
        filtered.append((source_id, entries, error))
    return filtered


class CabinetStore:
    def __init__(self) -> None:
        DATA.mkdir(exist_ok=True)
        BACKUP_DIR.mkdir(exist_ok=True)
        self.lock = threading.RLock()
        self.sync_lock = threading.Lock()
        self.collector_launch_lock = threading.Lock()
        self.collector_process: subprocess.Popen | None = None
        self.collector_refresh_timer: threading.Timer | None = None
        self.status = {
            "running": False,
            "phase": "idle",
            "checked": 0,
            "total": 0,
            "added": 0,
            "failed": 0,
            "message": "本机资料库已就绪",
            "lastSyncAt": None,
        }
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS article_content (
                    article_id TEXT PRIMARY KEY,
                    source_url TEXT NOT NULL,
                    html TEXT NOT NULL DEFAULT '',
                    plain_text TEXT NOT NULL DEFAULT '',
                    content_hash TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'ready',
                    error TEXT NOT NULL DEFAULT '',
                    fetched_at TEXT NOT NULL
                )
                """
            )
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS annotations (
                    id TEXT PRIMARY KEY,
                    article_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    quote TEXT NOT NULL,
                    prefix TEXT NOT NULL DEFAULT '',
                    suffix TEXT NOT NULL DEFAULT '',
                    block_index INTEGER NOT NULL DEFAULT 0,
                    start_offset INTEGER NOT NULL DEFAULT 0,
                    end_offset INTEGER NOT NULL DEFAULT 0,
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_annotations_article_updated ON annotations(article_id, updated_at DESC)"
            )
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS deleted_articles (
                    article_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL DEFAULT '',
                    url TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL DEFAULT '',
                    article_json TEXT,
                    deleted_at TEXT NOT NULL,
                    purge_after TEXT NOT NULL
                )
                """
            )
            db.execute("CREATE INDEX IF NOT EXISTS idx_deleted_articles_url ON deleted_articles(url)")
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_deleted_articles_source_title ON deleted_articles(source_id, title)"
            )
            db.execute(
                "UPDATE article_content SET status='failed', error='上次调阅已中断' WHERE status='loading'"
            )
            db.execute("PRAGMA optimize")
            db.commit()
        self.repair_article_summaries()

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(DB_PATH, timeout=20)

    def configured(self) -> bool:
        with self.connect() as db:
            return db.execute("SELECT 1 FROM kv WHERE key='state'").fetchone() is not None

    def repair_article_summaries(self) -> int:
        """Remove title fallbacks and reuse only content already cached locally."""
        with self.lock, self.connect() as db:
            row = db.execute("SELECT value FROM kv WHERE key='state'").fetchone()
            if not row:
                return 0
            try:
                state = json.loads(row[0])
            except json.JSONDecodeError:
                return 0
            cached_text = dict(
                db.execute(
                    "SELECT article_id, plain_text FROM article_content WHERE status='ready' AND plain_text != ''"
                ).fetchall()
            )
            changed = 0
            for article in state.get("articles", []):
                original = str(article.get("summary") or "").strip()
                summary = "" if is_duplicate_summary(article.get("title"), original) else finalize_summary(original)
                if not summary:
                    summary = summary_from_text(article.get("title"), cached_text.get(article.get("id"), ""))
                if article.get("summary") != summary:
                    article["summary"] = summary
                    changed += 1
            if changed:
                payload = json.dumps(state, ensure_ascii=False, separators=(",", ":"))
                db.execute(
                    "UPDATE kv SET value=? WHERE key='state'",
                    (payload,),
                )
                db.commit()
            return changed

    def load(self) -> dict:
        with self.lock, self.connect() as db:
            row = db.execute("SELECT value FROM kv WHERE key='state'").fetchone()
        if not row:
            return {"sources": [], "articles": []}
        try:
            state = json.loads(row[0])
        except json.JSONDecodeError:
            return {"sources": [], "articles": []}
        state.setdefault("sources", [])
        state.setdefault("articles", [])
        return state

    def save(self, state: dict) -> None:
        with self.lock, self.connect() as db:
            deleted_ids, deleted_urls, deleted_keys = self._deleted_fingerprints(db)
            articles = [
                article for article in state.get("articles", [])
                if not self._is_deleted_article(article, deleted_ids, deleted_urls, deleted_keys)
            ]
            safe_state = {"sources": state.get("sources", []), "articles": articles}
            self._update_source_counts(safe_state)
            payload = json.dumps(safe_state, ensure_ascii=False, separators=(",", ":"))
            db.execute(
                "INSERT INTO kv(key,value) VALUES('state',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (payload,),
            )
            db.commit()
        self.backup_once_daily()

    @staticmethod
    def _deleted_fingerprints(db: sqlite3.Connection) -> tuple[set[str], set[str], set[tuple[str, str]]]:
        rows = db.execute("SELECT article_id, source_id, url, title FROM deleted_articles").fetchall()
        return (
            {str(row[0]) for row in rows if row[0]},
            {str(row[2]) for row in rows if row[2]},
            {(str(row[1]), str(row[3])) for row in rows if row[1] and row[3]},
        )

    @staticmethod
    def _is_deleted_article(
        article: dict,
        deleted_ids: set[str],
        deleted_urls: set[str],
        deleted_keys: set[tuple[str, str]],
    ) -> bool:
        article_id = str(article.get("id") or "")
        url = str(article.get("url") or "")
        key = (str(article.get("source") or ""), str(article.get("title") or ""))
        return article_id in deleted_ids or bool(url and url in deleted_urls) or key in deleted_keys

    @staticmethod
    def _update_source_counts(state: dict) -> None:
        for source in state.get("sources", []):
            articles = [article for article in state.get("articles", []) if article.get("source") == source.get("id")]
            source["articles"] = len(articles)
            source["unread"] = sum(not article.get("read") for article in articles)

    def prune_trash(self) -> int:
        current = now_iso()
        with self.lock, self.connect() as db:
            expired = [
                row[0] for row in db.execute(
                    "SELECT article_id FROM deleted_articles WHERE article_json IS NOT NULL AND purge_after<=?",
                    (current,),
                ).fetchall()
            ]
            if not expired:
                return 0
            db.executemany("UPDATE deleted_articles SET article_json=NULL WHERE article_id=?", [(item,) for item in expired])
            db.executemany("DELETE FROM article_content WHERE article_id=?", [(item,) for item in expired])
            db.executemany("DELETE FROM annotations WHERE article_id=?", [(item,) for item in expired])
            db.commit()
            return len(expired)

    def list_trash(self) -> list[dict]:
        self.prune_trash()
        with self.lock, self.connect() as db:
            rows = db.execute(
                "SELECT article_id, article_json, deleted_at, purge_after FROM deleted_articles "
                "WHERE article_json IS NOT NULL ORDER BY deleted_at DESC"
            ).fetchall()
        items = []
        for article_id, article_json, deleted_at, purge_after in rows:
            try:
                article = json.loads(article_json)
            except (TypeError, json.JSONDecodeError):
                continue
            items.append({
                "articleId": article_id,
                "article": article,
                "deletedAt": deleted_at,
                "purgeAfter": purge_after,
            })
        return items

    def trash_articles(self, article_ids: list[str]) -> dict:
        requested = {str(item).strip() for item in article_ids if str(item).strip()}
        if not requested:
            raise ValueError("请选择至少一篇文章")
        deleted_at = datetime.now(timezone.utc)
        purge_after = deleted_at + timedelta(days=TRASH_RETENTION_DAYS)
        trashed = []
        with self.lock, self.connect() as db:
            row = db.execute("SELECT value FROM kv WHERE key='state'").fetchone()
            state = json.loads(row[0]) if row else {"sources": [], "articles": []}
            kept = []
            for article in state.get("articles", []):
                article_id = str(article.get("id") or "")
                if article_id not in requested:
                    kept.append(article)
                    continue
                db.execute(
                    """
                    INSERT INTO deleted_articles(
                        article_id, source_id, url, title, article_json, deleted_at, purge_after
                    ) VALUES(?,?,?,?,?,?,?)
                    ON CONFLICT(article_id) DO UPDATE SET
                        source_id=excluded.source_id,
                        url=excluded.url,
                        title=excluded.title,
                        article_json=excluded.article_json,
                        deleted_at=excluded.deleted_at,
                        purge_after=excluded.purge_after
                    """,
                    (
                        article_id,
                        str(article.get("source") or ""),
                        str(article.get("url") or ""),
                        str(article.get("title") or ""),
                        json.dumps(article, ensure_ascii=False, separators=(",", ":")),
                        deleted_at.isoformat(),
                        purge_after.isoformat(),
                    ),
                )
                trashed.append(article_id)
            state["articles"] = kept
            self._update_source_counts(state)
            payload = json.dumps(state, ensure_ascii=False, separators=(",", ":"))
            db.execute(
                "INSERT INTO kv(key,value) VALUES('state',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (payload,),
            )
            db.commit()
        self.backup_once_daily()
        return {"trashed": trashed, "trash": self.list_trash()}

    def restore_trash(self, article_ids: list[str]) -> dict:
        requested = {str(item).strip() for item in article_ids if str(item).strip()}
        if not requested:
            raise ValueError("请选择至少一篇文章")
        self.prune_trash()
        restored = []
        with self.lock, self.connect() as db:
            row = db.execute("SELECT value FROM kv WHERE key='state'").fetchone()
            state = json.loads(row[0]) if row else {"sources": [], "articles": []}
            existing_ids = {str(article.get("id") or "") for article in state.get("articles", [])}
            for article_id in requested:
                trash_row = db.execute(
                    "SELECT article_json FROM deleted_articles WHERE article_id=? AND article_json IS NOT NULL",
                    (article_id,),
                ).fetchone()
                if not trash_row:
                    continue
                try:
                    article = json.loads(trash_row[0])
                except (TypeError, json.JSONDecodeError):
                    continue
                if article_id not in existing_ids:
                    state.setdefault("articles", []).append(article)
                    existing_ids.add(article_id)
                db.execute("DELETE FROM deleted_articles WHERE article_id=?", (article_id,))
                restored.append(article_id)
            self._update_source_counts(state)
            payload = json.dumps(state, ensure_ascii=False, separators=(",", ":"))
            db.execute(
                "INSERT INTO kv(key,value) VALUES('state',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (payload,),
            )
            db.commit()
        self.backup_once_daily()
        return {"restored": restored, "trash": self.list_trash()}

    def purge_trash(self, article_ids: list[str] | None = None) -> dict:
        requested = {str(item).strip() for item in (article_ids or []) if str(item).strip()}
        with self.lock, self.connect() as db:
            if requested:
                targets = [
                    row[0] for row in db.execute(
                        f"SELECT article_id FROM deleted_articles WHERE article_json IS NOT NULL AND article_id IN ({','.join('?' for _ in requested)})",
                        tuple(requested),
                    ).fetchall()
                ]
            else:
                targets = [row[0] for row in db.execute(
                    "SELECT article_id FROM deleted_articles WHERE article_json IS NOT NULL"
                ).fetchall()]
            db.executemany("UPDATE deleted_articles SET article_json=NULL WHERE article_id=?", [(item,) for item in targets])
            db.executemany("DELETE FROM article_content WHERE article_id=?", [(item,) for item in targets])
            db.executemany("DELETE FROM annotations WHERE article_id=?", [(item,) for item in targets])
            db.commit()
        return {"purged": targets, "trash": self.list_trash()}

    def backup_once_daily(self) -> None:
        if not DB_PATH.exists():
            return
        target = BACKUP_DIR / f"cabinet-{datetime.now():%Y-%m-%d}.db"
        if target.exists():
            return
        try:
            with self.lock, self.connect() as source, sqlite3.connect(target) as destination:
                source.backup(destination)
        except sqlite3.Error:
            target.unlink(missing_ok=True)

    def export_backup(self) -> Path:
        target = BACKUP_DIR / "cabinet-export.db"
        target.unlink(missing_ok=True)
        with self.lock, self.connect() as source, sqlite3.connect(target) as destination:
            source.backup(destination)
        return target

    def get_article_content(self, article_id: str) -> dict | None:
        with self.lock, self.connect() as db:
            row = db.execute(
                "SELECT article_id, source_url, html, plain_text, content_hash, status, error, fetched_at "
                "FROM article_content WHERE article_id=?",
                (article_id,),
            ).fetchone()
        if not row:
            return None
        keys = ("articleId", "sourceUrl", "html", "text", "contentHash", "status", "error", "fetchedAt")
        return dict(zip(keys, row))

    def list_article_content_status(self) -> list[dict]:
        with self.lock, self.connect() as db:
            rows = db.execute(
                "SELECT article_id, status, error, fetched_at FROM article_content ORDER BY fetched_at DESC"
            ).fetchall()
        keys = ("articleId", "status", "error", "fetchedAt")
        return [dict(zip(keys, row)) for row in rows]

    def set_article_content_status(self, article_id: str, source_url: str, status: str, error: str = "") -> None:
        timestamp = now_iso()
        with self.lock, self.connect() as db:
            db.execute(
                """
                INSERT INTO article_content(article_id, source_url, status, error, fetched_at)
                VALUES(?,?,?,?,?)
                ON CONFLICT(article_id) DO UPDATE SET
                    source_url=excluded.source_url,
                    status=excluded.status,
                    error=excluded.error,
                    fetched_at=excluded.fetched_at
                """,
                (article_id, source_url, status, error[:1000], timestamp),
            )
            db.commit()

    def fetch_article_content(self, article_id: str, source_url: str, force: bool = False) -> dict:
        cached = self.get_article_content(article_id)
        if cached and cached.get("status") == "ready" and not force:
            return cached
        parsed = urlparse(source_url)
        if parsed.scheme != "https" or parsed.hostname != "mp.weixin.qq.com" or not parsed.path.startswith("/s"):
            self.set_article_content_status(article_id, source_url, "failed", "只支持公开的微信文章链接")
            raise ValueError("只支持公开的微信文章链接")

        self.set_article_content_status(article_id, source_url, "loading")
        payload = json.dumps({"url": source_url}, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            COLLECTOR_CONTENT_URL,
            data=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=105) as response:
                raw = response.read(MAX_ARTICLE_BYTES + 1)
            if len(raw) > MAX_ARTICLE_BYTES:
                raise ValueError("正文超过 4 MB，已停止缓存")
            result = json.loads(raw.decode("utf-8"))
            data = result.get("data") or {}
            article_html = str(data.get("html") or "").strip()
            plain_text = str(data.get("text") or "").strip()
            if not article_html or not plain_text:
                raise ValueError("采集器没有返回可阅读的正文")
        except urllib.error.HTTPError as error:
            try:
                detail = json.loads(error.read().decode("utf-8")).get("detail", {})
                message = detail.get("message") or detail.get("detail", {}).get("message")
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                message = None
            message = message or "正文调阅失败，请查看微信原文"
            self.set_article_content_status(article_id, source_url, "failed", message)
            raise ValueError(message) from error
        except (urllib.error.URLError, TimeoutError) as error:
            message = "公众号采集器未启动，暂时无法调阅正文"
            self.set_article_content_status(article_id, source_url, "failed", message)
            raise ValueError(message) from error
        except (ValueError, AttributeError, TypeError) as error:
            message = str(error) or "正文调阅失败，请查看微信原文"
            self.set_article_content_status(article_id, source_url, "failed", message)
            raise ValueError(message) from error

        fetched_at = now_iso()
        content_hash = hashlib.sha256(plain_text.encode("utf-8")).hexdigest()
        with self.lock, self.connect() as db:
            db.execute(
                """
                INSERT INTO article_content(article_id, source_url, html, plain_text, content_hash, status, error, fetched_at)
                VALUES(?,?,?,?,?,'ready','',?)
                ON CONFLICT(article_id) DO UPDATE SET
                    source_url=excluded.source_url,
                    html=excluded.html,
                    plain_text=excluded.plain_text,
                    content_hash=excluded.content_hash,
                    status='ready',
                    error='',
                    fetched_at=excluded.fetched_at
                """,
                (article_id, source_url, article_html, plain_text, content_hash, fetched_at),
            )
            db.commit()
        publish_time = int(data.get("publish_time") or 0)
        description = str(data.get("description") or "").strip()
        published_at = datetime.fromtimestamp(publish_time, tz=timezone.utc).isoformat() if publish_time else None
        if publish_time or description or plain_text:
            state = self.load()
            article = next((item for item in state["articles"] if item.get("id") == article_id), None)
            if article:
                changed = False
                if publish_time and article.get("publishedAt") != published_at:
                    article["publishedAt"] = published_at
                    article.pop("hours", None)
                    changed = True
                summary = finalize_summary(description) if not is_duplicate_summary(article.get("title"), description) else ""
                if not summary:
                    summary = summary_from_text(article.get("title"), plain_text)
                if summary and article.get("summary") != summary:
                    article["summary"] = summary
                    changed = True
                elif is_duplicate_summary(article.get("title"), article.get("summary")):
                    article["summary"] = ""
                    changed = True
                if changed:
                    self.save(state)
        content = self.get_article_content(article_id) or {}
        if published_at:
            content["publishedAt"] = published_at
        return content

    def list_annotations(self, article_id: str | None = None) -> list[dict]:
        query = (
            "SELECT id, article_id, kind, quote, prefix, suffix, block_index, start_offset, end_offset, "
            "note, created_at, updated_at FROM annotations"
        )
        params: tuple = ()
        if article_id:
            query += " WHERE article_id=?"
            params = (article_id,)
        query += " ORDER BY updated_at DESC"
        with self.lock, self.connect() as db:
            rows = db.execute(query, params).fetchall()
        keys = (
            "id", "articleId", "kind", "quote", "prefix", "suffix", "blockIndex",
            "startOffset", "endOffset", "note", "createdAt", "updatedAt",
        )
        return [dict(zip(keys, row)) for row in rows]

    def save_annotation(self, row: dict) -> dict:
        article_id = str(row.get("articleId") or "").strip()
        quote = str(row.get("quote") or "").strip()
        if not article_id or not quote:
            raise ValueError("批注缺少文章或选中文字")
        annotation_id = str(row.get("id") or f"n{uuid4().hex}")
        kind = "note" if row.get("kind") == "note" else "highlight"
        now = now_iso()
        existing = next((item for item in self.list_annotations(article_id) if item["id"] == annotation_id), None)
        created_at = existing["createdAt"] if existing else now
        values = (
            annotation_id,
            article_id,
            kind,
            quote[:4000],
            str(row.get("prefix") or "")[-160:],
            str(row.get("suffix") or "")[:160],
            max(0, int(row.get("blockIndex") or 0)),
            max(0, int(row.get("startOffset") or 0)),
            max(0, int(row.get("endOffset") or 0)),
            str(row.get("note") or "")[:12000],
            created_at,
            now,
        )
        with self.lock, self.connect() as db:
            db.execute(
                """
                INSERT INTO annotations(
                    id, article_id, kind, quote, prefix, suffix, block_index,
                    start_offset, end_offset, note, created_at, updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    kind=excluded.kind,
                    quote=excluded.quote,
                    prefix=excluded.prefix,
                    suffix=excluded.suffix,
                    block_index=excluded.block_index,
                    start_offset=excluded.start_offset,
                    end_offset=excluded.end_offset,
                    note=excluded.note,
                    updated_at=excluded.updated_at
                """,
                values,
            )
            db.commit()
        return next(item for item in self.list_annotations(article_id) if item["id"] == annotation_id)

    def delete_annotation(self, annotation_id: str) -> bool:
        with self.lock, self.connect() as db:
            cursor = db.execute("DELETE FROM annotations WHERE id=?", (annotation_id,))
            db.commit()
        return cursor.rowcount > 0

    def annotated_article_ids(self) -> set[str]:
        with self.lock, self.connect() as db:
            return {row[0] for row in db.execute("SELECT DISTINCT article_id FROM annotations")}

    def import_sources(self, rows: list[dict]) -> dict:
        state = self.load()
        sources = state["sources"]
        seen = {(source.get("feedUrl") or "").strip().lower(): source for source in sources if source.get("feedUrl")}
        added = 0
        updated = 0
        for index, row in enumerate(rows):
            name = str(row.get("name") or "").strip()
            feed_url = str(row.get("feedUrl") or "").strip()
            if not name or not feed_url or urlparse(feed_url).scheme not in {"http", "https"}:
                continue
            tier = str(row.get("tier") or "B").upper()
            tier = tier if tier in {"A", "B", "C"} else "B"
            existing = seen.get(feed_url.lower())
            values = {
                "name": name,
                "feedUrl": feed_url,
                "description": str(row.get("description") or "微信公众号订阅来源。").strip(),
                "tier": tier,
                "category": str(row.get("category") or "OTHER").upper(),
                "inbox": bool(row.get("inbox", tier == "A")),
                "enabled": bool(row.get("enabled", True)),
            }
            if existing:
                existing.update(values)
                updated += 1
            else:
                source = {
                    "id": f"s{int(time.time() * 1000)}{index}",
                    **values,
                    "articles": 0,
                    "unread": 0,
                    "last": "尚未同步",
                    "lastSyncAt": None,
                }
                sources.append(source)
                seen[feed_url.lower()] = source
                added += 1
        self.save(state)
        return {"added": added, "updated": updated, "total": len(sources)}

    def list_collector_sources(self) -> list[dict]:
        """Read local collector subscriptions without exposing its admin token."""
        if not COLLECTOR_DB_PATH.exists():
            raise ValueError("公众号采集器资料库尚未建立")
        try:
            with sqlite3.connect(COLLECTOR_DB_PATH, timeout=5) as db:
                rows = db.execute(
                    """
                    SELECT id, mp_name, mp_intro, status, sync_time, update_time
                    FROM feeds
                    WHERE id != 'MP_WXS_FEATURED_ARTICLES'
                    ORDER BY mp_name COLLATE NOCASE
                    """
                ).fetchall()
        except sqlite3.Error as error:
            raise ValueError(f"无法读取公众号采集器：{error}") from error
        return [
            {
                "id": row[0],
                "name": row[1] or row[0],
                "description": row[2] or "微信公众号订阅来源。",
                "enabled": bool(row[3]),
                "syncTime": row[4] or 0,
                "updateTime": row[5] or 0,
                "feedUrl": f"http://127.0.0.1:8001/feed/{row[0]}.rss",
            }
            for row in rows
        ]

    def collector_status(self) -> dict:
        request = urllib.request.Request(COLLECTOR_BASE_URL, headers={"User-Agent": "21st-Century-Cabinet/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=1.5) as response:
                if response.status < 500:
                    return {"ready": True, "state": "ready", "url": COLLECTOR_ADD_URL}
        except urllib.error.HTTPError as error:
            if error.code < 500:
                return {"ready": True, "state": "ready", "url": COLLECTOR_ADD_URL}
        except (urllib.error.URLError, TimeoutError, OSError):
            pass

        process = self.collector_process
        if process is not None:
            exit_code = process.poll()
            if exit_code is None:
                return {"ready": False, "state": "starting", "url": COLLECTOR_ADD_URL}
            return {
                "ready": False,
                "state": "failed",
                "url": COLLECTOR_ADD_URL,
                "error": (
                    f"采集器启动进程已退出（代码 {exit_code}），请查看 "
                    + ("we-mp-rss/data/logs/collector-error.log。" if COLLECTOR_DB_PATH.exists() else "弹出的启动窗口。")
                ),
            }
        return {"ready": False, "state": "stopped", "url": COLLECTOR_ADD_URL}

    def start_collector(self) -> dict:
        status = self.collector_status()
        if status["ready"] or status["state"] == "starting":
            return status
        collector_entry = COLLECTOR_ROOT / "main.py"
        can_start_directly = COLLECTOR_DB_PATH.exists() and COLLECTOR_PYTHON.exists() and collector_entry.exists()
        if not can_start_directly and RELEASE_MODE:
            raise ValueError("公众号采集器尚未完成首次初始化，请重新打开“21世纪内阁”应用")
        if not can_start_directly and not COLLECTOR_LAUNCHER.exists():
            raise ValueError("找不到公众号采集器启动脚本")

        with self.collector_launch_lock:
            status = self.collector_status()
            if status["ready"] or status["state"] == "starting":
                return status
            try:
                if can_start_directly:
                    log_root = COLLECTOR_DATA / "logs"
                    log_root.mkdir(parents=True, exist_ok=True)
                    environment = os.environ.copy()
                    environment["WERSS_ADMIN_USER"] = "admin"
                    with (log_root / "collector.log").open("a", encoding="utf-8") as stdout_log, (
                        log_root / "collector-error.log"
                    ).open("a", encoding="utf-8") as stderr_log:
                        self.collector_process = subprocess.Popen(
                            [
                                str(COLLECTOR_PYTHON),
                                str(collector_entry),
                                "-config",
                                str(COLLECTOR_CONFIG),
                                "-job",
                                "True",
                                "-init",
                                "True",
                            ],
                            cwd=str(COLLECTOR_WORKDIR),
                            env=environment,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                            stdout=stdout_log,
                            stderr=stderr_log,
                        )
                else:
                    self.collector_process = subprocess.Popen(
                        [
                            "powershell.exe",
                            "-NoProfile",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-File",
                            str(COLLECTOR_LAUNCHER),
                        ],
                        cwd=str(ROOT),
                        creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
                    )
            except OSError as error:
                raise ValueError(f"无法启动公众号采集器：{error}") from error
        return {"ready": False, "state": "starting", "url": COLLECTOR_ADD_URL}

    def schedule_collector_refresh(self, delay: float = 12) -> None:
        """Debounce collector webhooks, then read all updated RSS feeds once."""
        with self.lock:
            if self.collector_refresh_timer and self.collector_refresh_timer.is_alive():
                self.collector_refresh_timer.cancel()

            def refresh() -> None:
                # The collector has already finished its own update. Only read
                # the refreshed RSS here; do not start another collection run.
                self.start_sync(force=True, collect_collector=False)

            self.collector_refresh_timer = threading.Timer(delay, refresh)
            self.collector_refresh_timer.daemon = True
            self.collector_refresh_timer.start()
            self.status["message"] = "采集器已有更新，正在等待本轮采集完成"

    def source_due(self, source: dict, force: bool) -> bool:
        if not source.get("enabled") or not source.get("feedUrl"):
            return False
        if force or not source.get("lastSyncAt"):
            return True
        try:
            last = datetime.fromisoformat(str(source["lastSyncAt"]).replace("Z", "+00:00"))
        except ValueError:
            return True
        return (datetime.now(timezone.utc) - last).total_seconds() >= SYNC_INTERVALS.get(source.get("tier", "B"), 86400)

    def start_sync(self, force: bool = False, collect_collector: bool = False) -> bool:
        if self.status["running"]:
            return False
        thread = threading.Thread(
            target=self._sync,
            args=(force, collect_collector),
            daemon=True,
            name="cabinet-sync",
        )
        thread.start()
        return True

    def _sync(self, force: bool, collect_collector: bool = False) -> None:
        if not self.sync_lock.acquire(blocking=False):
            return
        try:
            state = self.load()
            targets = [source for source in state["sources"] if self.source_due(source, force)]
            targets.sort(key=lambda source: ({"A": 0, "B": 1, "C": 2}.get(source.get("tier"), 1), source.get("name", "")))
            self.status.update({"running": True, "phase": "syncing", "checked": 0, "total": len(targets), "added": 0, "failed": 0, "message": "正在优先同步 A 级来源"})
            if not targets:
                self.status.update({"running": False, "phase": "idle", "message": "所有来源都已是最新"})
                return
            collector_targets = [
                source for source in targets
                if str(source.get("feedUrl") or "").startswith("http://127.0.0.1:8001/feed/")
            ]
            collector_error = ""
            if collect_collector and collector_targets:
                try:
                    self._collect_subscribed_accounts()
                except Exception as error:  # noqa: BLE001 - continue importing existing RSS
                    collector_error = str(error)
            results = []
            self.status.update({"phase": "syncing", "checked": 0, "total": len(targets), "message": "正在读取全部信息源"})
            with ThreadPoolExecutor(max_workers=2, thread_name_prefix="feed") as pool:
                future_map = {pool.submit(fetch_feed, source): source for source in targets}
                for future in as_completed(future_map):
                    source = future_map[future]
                    try:
                        results.append((source["id"], future.result(), None))
                    except Exception as error:  # noqa: BLE001 - local service reports per-source failure
                        results.append((source["id"], [], str(error)))
                    self.status["checked"] += 1
            results = latest_collector_entries(
                results,
                {source["id"] for source in collector_targets},
            )
            by_source = {source["id"]: source for source in state["sources"]}
            existing_by_url = {article.get("url"): article for article in state["articles"] if article.get("url")}
            existing_by_key = {(article.get("source"), article.get("title")): article for article in state["articles"]}
            with self.connect() as db:
                deleted_ids, deleted_urls, deleted_keys = self._deleted_fingerprints(db)
            for source_id, entries, error in results:
                source = by_source.get(source_id)
                if not source:
                    continue
                source["lastSyncAt"] = now_iso()
                if error:
                    source["last"] = "同步失败"
                    source["lastError"] = error[:180]
                    self.status["failed"] += 1
                    continue
                source.pop("lastError", None)
                source["last"] = "刚刚"
                for entry in entries:
                    key = (source_id, entry["title"])
                    entry["source"] = source_id
                    if self._is_deleted_article(entry, deleted_ids, deleted_urls, deleted_keys):
                        continue
                    existing = existing_by_url.get(entry.get("url")) or existing_by_key.get(key)
                    if existing:
                        # Refresh source metadata while preserving read/saved/progress state.
                        for field in ("publishedAt", "summary", "author", "cover", "mins"):
                            if entry.get(field):
                                existing[field] = entry[field]
                        existing.pop("hours", None)
                        continue
                    state["articles"].append(entry)
                    if entry.get("url"):
                        existing_by_url[entry["url"]] = entry
                    existing_by_key[key] = entry
                    self.status["added"] += 1
            self.apply_retention(state)
            for source in state["sources"]:
                articles = [article for article in state["articles"] if article.get("source") == source.get("id")]
                source["articles"] = len(articles)
                source["unread"] = sum(not article.get("read") for article in articles)
            self.save(state)
            self.backup_once_daily()
            self.status.update({
                "running": False,
                "phase": "idle",
                "lastSyncAt": now_iso(),
                "message": (
                    f"同步完成：新增 {self.status['added']} 篇，失败 {self.status['failed']} 个来源"
                    + (f"；公众号采集器：{collector_error}" if collector_error else "")
                ),
            })
        finally:
            self.status["running"] = False
            self.sync_lock.release()

    def _collector_json(self, url: str, method: str = "GET", timeout: float = 8) -> dict:
        body = b"{}" if method == "POST" else None
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "21st-Century-Cabinet/1.0",
            },
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f"无法连接公众号采集器：{error}") from error
        if payload.get("code") != 0:
            raise RuntimeError(str(payload.get("message") or "公众号采集器返回错误"))
        return payload.get("data") or {}

    def _collect_subscribed_accounts(self, timeout: float = 600) -> None:
        """Start collector work and wait until its queue has drained."""
        result = self._collector_json(COLLECTOR_SYNC_URL, method="POST")
        total = int(result.get("total") or result.get("queue", {}).get("pending_count") or 0)
        deadline = time.monotonic() + timeout
        self.status.update({
            "phase": "collecting",
            "checked": 0,
            "total": total,
            "message": "正在采集公众号最新文章",
        })
        while time.monotonic() < deadline:
            queue_status = self._collector_json(COLLECTOR_SYNC_STATUS_URL)
            pending = int(queue_status.get("pending_count") or 0)
            current = queue_status.get("current_task")
            if total:
                self.status["checked"] = max(0, total - pending - (1 if current else 0))
            if pending == 0 and not current:
                return
            time.sleep(1)
        raise RuntimeError("公众号采集超过 10 分钟仍未完成")

    def apply_retention(self, state: dict) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
        annotated = self.annotated_article_ids()
        kept = []
        for article in state["articles"]:
            progress = float(article.get("progress") or 0)
            if article.get("saved") or article.get("id") in annotated or 0 < progress < 0.95 or not article.get("publishedAt"):
                kept.append(article)
                continue
            try:
                published = datetime.fromisoformat(str(article["publishedAt"]).replace("Z", "+00:00"))
            except ValueError:
                kept.append(article)
                continue
            if published >= cutoff:
                kept.append(article)
        state["articles"] = kept


def fetch_feed(source: dict) -> list[dict]:
    request = urllib.request.Request(
        source["feedUrl"],
        headers={
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
            "User-Agent": "21st-Century-Cabinet/1.0 (personal feed reader)",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            payload = response.read(MAX_FEED_BYTES + 1)
    except urllib.error.URLError as error:
        raise RuntimeError(f"网络错误：{error.reason}") from error
    if len(payload) > MAX_FEED_BYTES:
        raise RuntimeError("订阅源超过 8 MB，已停止读取")
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as error:
        raise RuntimeError("订阅源不是有效的 RSS/Atom") from error
    nodes = [node for node in root.iter() if local_name(node.tag) in {"item", "entry"}][:30]
    items = []
    for index, node in enumerate(nodes):
        title = clean_text(first_text(node, "title"))
        link = entry_link(node)
        if not title:
            continue
        raw = first_text(node, "encoded", "content", "description", "summary")
        body = clean_text(raw)
        summary = "" if is_duplicate_summary(title, body) else finalize_summary(body)
        published = parse_published(first_text(node, "pubdate", "published", "updated", "date"))
        items.append({
            "id": f"a{int(time.time() * 1000)}{index}",
            "title": title,
            "summary": summary,
            "author": clean_text(first_text(node, "author", "creator")) or source.get("name", "未知来源"),
            "mins": max(3, min(30, round(len(body) / 500) or 5)),
            "read": False,
            "saved": False,
            "progress": 0,
            "tags": [],
            "cover": urljoin(source["feedUrl"], entry_cover(node, raw)),
            "url": urljoin(source["feedUrl"], link),
            "content": [body or "正文将在打开原文时获取。"],
            "publishedAt": published.astimezone(timezone.utc).isoformat() if published else None,
        })
    return items


STORE = CabinetStore()


class CabinetHandler(SimpleHTTPRequestHandler):
    server_version = "CabinetLocal/1.0"

    def log_message(self, format: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")

    def send_json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 12 * 1024 * 1024:
            raise ValueError("请求内容过大")
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self) -> None:  # noqa: N802 - stdlib hook name
        parsed = urlsplit(self.path)
        path = parsed.path
        if path == "/api/article-content":
            article_id = (parse_qs(parsed.query).get("articleId") or [""])[0].strip()
            if not article_id:
                self.send_json({"ok": False, "error": "缺少文章 ID"}, 400)
                return
            cached = STORE.get_article_content(article_id)
            if not cached:
                self.send_json({"ok": False, "error": "正文尚未缓存"}, 404)
                return
            self.send_json({"ok": True, "content": cached})
            return
        if path == "/api/article-content-status":
            self.send_json({"ok": True, "articles": STORE.list_article_content_status()})
            return
        if path == "/api/annotations":
            article_id = (parse_qs(parsed.query).get("articleId") or [""])[0].strip() or None
            self.send_json({"ok": True, "annotations": STORE.list_annotations(article_id)})
            return
        if path == "/api/trash":
            self.send_json({"ok": True, "trash": STORE.list_trash(), "retentionDays": TRASH_RETENTION_DAYS})
            return
        if path == "/api/state":
            state = STORE.load()
            self.send_json({
                **state,
                "configured": STORE.configured(),
                "retentionDays": RETENTION_DAYS,
                "version": CURRENT_VERSION,
            })
            return
        if path == "/api/check-update":
            try:
                self.send_json(check_for_update())
            except ValueError as error:
                self.send_json({"ok": False, "error": str(error)}, HTTPStatus.SERVICE_UNAVAILABLE)
            return
        if path == "/api/collector-sources":
            try:
                self.send_json({"ok": True, "sources": STORE.list_collector_sources()})
            except ValueError as error:
                self.send_json({"ok": False, "error": str(error)}, 503)
            return
        if path == "/api/collector-status":
            self.send_json({"ok": True, **STORE.collector_status()})
            return
        if path == "/api/status":
            self.send_json(dict(STORE.status))
            return
        if path == "/api/backup":
            target = STORE.export_backup()
            data = target.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/vnd.sqlite3")
            self.send_header("Content-Disposition", f'attachment; filename="cabinet-{datetime.now():%Y-%m-%d-%H%M%S}.db"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802 - stdlib hook name
        try:
            body = self.read_json()
            path = urlsplit(self.path).path
            if path == "/api/article-content":
                article_id = str(body.get("articleId") or "").strip()
                source_url = str(body.get("url") or "").strip()
                if not article_id or not source_url:
                    raise ValueError("缺少文章 ID 或原文链接")
                content = STORE.fetch_article_content(article_id, source_url, force=bool(body.get("force")))
                self.send_json({"ok": True, "content": content})
                return
            if path == "/api/annotations":
                annotation = STORE.save_annotation(body)
                self.send_json({"ok": True, "annotation": annotation})
                return
            if path == "/api/state":
                if not isinstance(body.get("sources"), list) or not isinstance(body.get("articles"), list):
                    raise ValueError("state 格式不正确")
                STORE.save(body)
                self.send_json({"ok": True})
                return
            if path == "/api/articles/trash":
                article_ids = body.get("articleIds", [])
                if not isinstance(article_ids, list):
                    raise ValueError("articleIds 必须是数组")
                self.send_json({"ok": True, **STORE.trash_articles(article_ids)})
                return
            if path == "/api/trash/restore":
                article_ids = body.get("articleIds", [])
                if not isinstance(article_ids, list):
                    raise ValueError("articleIds 必须是数组")
                self.send_json({"ok": True, **STORE.restore_trash(article_ids)})
                return
            if path == "/api/trash/purge":
                article_ids = body.get("articleIds")
                if article_ids is not None and not isinstance(article_ids, list):
                    raise ValueError("articleIds 必须是数组")
                self.send_json({"ok": True, **STORE.purge_trash(article_ids)})
                return
            if path == "/api/import-sources":
                rows = body.get("sources", [])
                if not isinstance(rows, list):
                    raise ValueError("sources 必须是数组")
                self.send_json({"ok": True, **STORE.import_sources(rows)})
                return
            if path == "/api/collector-updated":
                STORE.schedule_collector_refresh()
                self.send_json({"ok": True, "message": "已安排读取采集器的新文章"}, 202)
                return
            if path == "/api/start-collector":
                result = STORE.start_collector()
                self.send_json({"ok": True, **result}, 200 if result["ready"] else 202)
                return
            if path == "/api/sync":
                force = bool(body.get("force"))
                started = STORE.start_sync(force=force, collect_collector=force)
                self.send_json({"ok": True, "started": started, "status": dict(STORE.status)}, 202)
                return
            self.send_error(HTTPStatus.NOT_FOUND)
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json({"ok": False, "error": str(error)}, 400)

    def do_DELETE(self) -> None:  # noqa: N802 - stdlib hook name
        path = urlsplit(self.path).path
        prefix = "/api/annotations/"
        if path.startswith(prefix):
            annotation_id = path[len(prefix):].strip()
            if not annotation_id:
                self.send_json({"ok": False, "error": "缺少批注 ID"}, 400)
                return
            deleted = STORE.delete_annotation(annotation_id)
            self.send_json({"ok": deleted}, 200 if deleted else 404)
            return
        self.send_error(HTTPStatus.NOT_FOUND)


def scheduler() -> None:
    time.sleep(4)
    STORE.start_sync(force=False)
    while True:
        time.sleep(300)
        STORE.start_sync(force=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="21世纪内阁本机伴侣服务")
    parser.add_argument("--port", type=int, default=4173)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    handler = partial(CabinetHandler, directory=str(DIST))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    threading.Thread(target=scheduler, daemon=True, name="cabinet-scheduler").start()
    url = f"http://127.0.0.1:{args.port}/"
    print(f"21世纪内阁已启动：{url}")
    print(f"本机资料库：{DB_PATH}")
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n21世纪内阁已停止。")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
