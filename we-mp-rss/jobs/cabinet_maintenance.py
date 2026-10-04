"""Local integration jobs for the 21st Century Cabinet reader."""

from __future__ import annotations

import threading
import time
import urllib.request
from datetime import datetime

from core.cache import clear_cache_pattern
from core.db import DB
from core.models.article import Article
from core.models.base import DATA_STATUS
from core.models.feed import Feed
from core.models.message_task import MessageTask
from core.print import print_info, print_success, print_warning
from core.rss import RSS


CABINET_TASK_ID = "cabinet-low-frequency"
CABINET_SYNC_INTERVAL_SECONDS = 12 * 60 * 60
CABINET_WEBHOOK_URL = "http://127.0.0.1:4173/api/collector-updated"


def build_cabinet_task() -> MessageTask:
    """Build an internal all-feed task without exposing it to generic schedulers."""
    session = DB.get_session()
    try:
        # An earlier implementation persisted this task. The collector has two
        # generic MessageTask schedulers, so a persisted active row could run
        # twice. Remove that migration row and register the job exactly once
        # on the local collection scheduler below.
        session.query(MessageTask).filter(MessageTask.id == CABINET_TASK_ID).delete()
        session.commit()
    finally:
        session.close()
    now = datetime.now()
    return MessageTask(
        id=CABINET_TASK_ID,
        name="21世纪内阁低频同步",
        message_type=1,
        message_template="{}",
        web_hook_url=CABINET_WEBHOOK_URL,
        headers="{}",
        cookies="",
        mps_id="[]",
        cron_exp="0 */12 * * *",
        status=0,
        created_at=now,
        updated_at=now,
    )


def schedule_cabinet_task(task: MessageTask) -> None:
    """Register one private twice-daily job on the collector scheduler."""
    from jobs.mps import add_job, scheduler

    if CABINET_TASK_ID not in scheduler.get_job_ids():
        scheduler.add_cron_job(
            add_job,
            cron_expr=task.cron_exp,
            kwargs={"task": task},
            job_id=CABINET_TASK_ID,
            tag="21世纪内阁低频同步",
        )
    scheduler.start()


def collection_is_overdue() -> bool:
    """Treat a collection as due when any enabled feed is older than 12 hours."""
    session = DB.get_session()
    try:
        feeds = session.query(Feed).filter(Feed.status == DATA_STATUS.ACTIVE).all()
        if not feeds:
            return False
        cutoff = int(time.time()) - CABINET_SYNC_INTERVAL_SECONDS
        return any(int(feed.sync_time or 0) < cutoff for feed in feeds)
    finally:
        session.close()


def notify_cabinet() -> bool:
    request = urllib.request.Request(
        CABINET_WEBHOOK_URL,
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return 200 <= response.status < 300
    except Exception as exc:
        print_warning(f"21世纪内阁暂未运行，稍后打开时会读取最新 RSS：{exc}")
        return False


def backfill_missing_publish_times(limit: int = 30) -> dict:
    """Repair legacy rows using only timestamps extracted from the original page."""
    from core.article_content import fetch_article_snapshot

    session = DB.get_session()
    repaired = 0
    checked = 0
    failed = 0
    changed_feed_ids: set[str] = set()
    try:
        articles = (
            session.query(Article)
            .filter(
                Article.status == DATA_STATUS.ACTIVE,
                (Article.publish_time.is_(None)) | (Article.publish_time <= 0),
                Article.url.isnot(None),
                Article.url != "",
            )
            .order_by(Article.created_at.asc())
            .limit(limit)
            .all()
        )
        for article in articles:
            checked += 1
            try:
                snapshot = fetch_article_snapshot(article.url, preferred_mode="web", timeout=75)
                publish_time = int(snapshot.get("publish_time") or 0)
                if publish_time <= 0:
                    continue
                article.publish_time = publish_time
                article.updated_at = int(time.time())
                article.updated_at_millis = int(time.time() * 1000)
                changed_feed_ids.add(article.mp_id)
                repaired += 1
                session.commit()
            except Exception as exc:
                session.rollback()
                failed += 1
                print_warning(f"发布时间补取失败 [{article.title}]：{exc}")
        if repaired:
            for feed_id in changed_feed_ids:
                RSS().clear_cache(mp_id=feed_id)
            clear_cache_pattern("articles_list")
            clear_cache_pattern("article_detail")
            clear_cache_pattern("home_page")
            notify_cabinet()
        return {"checked": checked, "repaired": repaired, "failed": failed}
    finally:
        session.close()


def _startup_maintenance(task: MessageTask) -> None:
    if collection_is_overdue():
        from jobs.mps import add_job

        print_info("公众号来源超过 12 小时未同步，已加入后台低频采集队列")
        add_job(task=task)
    result = backfill_missing_publish_times()
    print_success(
        "发布时间检查完成："
        f"检查 {result['checked']} 篇，补齐 {result['repaired']} 篇，失败 {result['failed']} 篇"
    )


def start_cabinet_maintenance() -> MessageTask:
    """Ensure scheduling exists and run non-blocking startup maintenance."""
    task = build_cabinet_task()
    schedule_cabinet_task(task)
    threading.Thread(
        target=_startup_maintenance,
        args=(task,),
        daemon=True,
        name="cabinet-maintenance",
    ).start()
    return task
