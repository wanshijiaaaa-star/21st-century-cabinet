import threading
from core import lax, thread
from core.models import Article, Feed, DATA_STATUS
from core.db import DB
from core.print import print_info, print_error
from core.redis_client import RedisCache

# 创建文章统计专用的 Redis 缓存实例
article_cache = RedisCache(key_prefix="werss:article")


class ArticleInfo():
    """文章统计信息"""
    # 没有内容的文章数量
    no_content_count: int = 0
    # 有内容的文章数量
    has_content_count: int = 0
    # 所有文章数量
    all_count: int = 0
    # 不正常的文章数量
    wrong_count: int = 0
    # 公众号总数
    mp_all_count: int = 0


def laxArticle():
    """统计文章信息 - 使用 has_content 字段优化性能"""
    info = ArticleInfo()
    session = DB.get_session()
    try:
        from sqlalchemy import text

        # 使用 has_content 字段进行统计，避免扫描大文本字段
        sql = text("""
            SELECT
                COUNT(*) as all_count,
                SUM(CASE WHEN has_content = 0 THEN 1 ELSE 0 END) as no_content_count,
                SUM(CASE WHEN status != 1 THEN 1 ELSE 0 END) as wrong_count
            FROM articles
            WHERE status != 1000
        """)

        result = session.execute(sql).fetchone()

        if result:
            info.all_count = int(result[0] or 0)
            info.no_content_count = int(result[1] or 0)
            info.wrong_count = int(result[2] or 0)
            info.has_content_count = info.all_count - info.no_content_count

        # 公众号总数 - 单独查询，因为跨表
        info.mp_all_count = session.query(Feed.id).distinct().count()

        return info.__dict__
    finally:
        session.close()


# 本地缓存（Redis 不可用时的降级方案）
ARTICLE_INFO = {}
lock = threading.Lock()


def refresh_article_info():
    """刷新文章统计信息"""
    def lax_article():
        global ARTICLE_INFO
        with lock:
            ARTICLE_INFO = laxArticle()
            # 保存到 Redis
            if article_cache.set("info", ARTICLE_INFO):
                print_info(f"文章统计已更新并保存到 Redis: {ARTICLE_INFO}")
            else:
                print_info(f"文章统计已更新（本地缓存）: {ARTICLE_INFO}")
    
    threading.Thread(target=lax_article, daemon=True).start()


def get_article_info():
    """获取文章统计信息
    
    优先从 Redis 获取，如果 Redis 不可用则使用本地缓存
    """
    global ARTICLE_INFO
    
    # 先尝试从 Redis 获取
    redis_data = article_cache.get("info")
    if redis_data is not None:
        with lock:
            ARTICLE_INFO = redis_data
        return redis_data
    
    # Redis 不可用，触发刷新
    refresh_article_info()
    
    # 返回本地缓存
    with lock:
        return ARTICLE_INFO

