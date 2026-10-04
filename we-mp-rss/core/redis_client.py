"""Redis客户端工具类"""
import json
import redis
from typing import Optional, Dict, Any
from datetime import datetime
from core.config import cfg
from core.print import print_error, print_info, print_warning


class RedisClient:
    """Redis客户端封装类"""
    
    _instance: Optional['RedisClient'] = None
    _client: Optional[redis.Redis] = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化Redis连接"""
        if self._client is not None:
            return
            
        redis_url = cfg.get("redis.url", "")
        
        if not redis_url:
            print_info("Redis URL未配置，统计功能将禁用")
            return
            
        try:
            self._client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            # 测试连接
            self._client.ping()
            print_info("Redis连接成功")
        except redis.exceptions.ConnectionError as e:
            print_error(f"Redis连接失败 - 无法连接到Redis服务")
            print_error(f"  错误详情: {e}")
            print_error(f"  请检查:")
            print_error(f"    1. Redis服务是否已启动")
            print_error(f"    2. 配置的地址和端口是否正确")
            print_error(f"    3. 防火墙是否允许连接")
            print_error(f"  运行诊断: python diagnose_redis.py")
            self._client = None
        except redis.exceptions.AuthenticationError as e:
            print_error(f"Redis连接失败 - 认证错误")
            print_error(f"  错误详情: {e}")
            print_error(f"  请检查Redis密码配置是否正确")
            self._client = None
        except redis.exceptions.TimeoutError as e:
            print_error(f"Redis连接失败 - 连接超时")
            print_error(f"  错误详情: {e}")
            print_error(f"  请检查网络连接和Redis服务状态")
            self._client = None
        except Exception as e:
            print_error(f"Redis连接失败: {type(e).__name__} - {e}")
            self._client = None
    
    def reconnect(self) -> bool:
        """重新连接Redis
        
        Returns:
            是否重新连接成功
        """
        if self._client is not None:
            try:
                self._client.ping()
                return True
            except:
                pass
        
        # 重置客户端
        self._client = None
        self.__init__()
        return self.is_connected
    
    @property
    def is_connected(self) -> bool:
        """检查Redis是否已连接"""
        return self._client is not None
    
    def record_env_exception(self, url: str, mp_name: str = "", mp_id: str = "") -> bool:
        """记录环境异常统计
        
        Args:
            url: 文章URL
            mp_name: 公众号名称
            mp_id: 公众号ID
            
        Returns:
            是否记录成功
        """
        if not self.is_connected:
            # 尝试重新连接
            if not self.reconnect():
                return False
            
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 使用Redis事务确保原子性
            pipe = self._client.pipeline()
            
            # 1. 总计数器 (按日期)
            pipe.incr(f"werss:env_exception:total:{today}")
            pipe.expire(f"werss:env_exception:total:{today}", 86400 * 30)  # 保留30天
            
            # 2. URL维度统计 (按日期)
            url_key = f"werss:env_exception:url:{today}"
            pipe.hset(url_key, url, timestamp)
            pipe.expire(url_key, 86400 * 30)  # 保留30天
            
            # 3. 公众号维度统计 (按日期)
            if mp_id:
                mp_key = f"werss:env_exception:mp:{today}"
                pipe.hincrby(mp_key, mp_id, 1)
                pipe.expire(mp_key, 86400 * 30)  # 保留30天
            
            # 4. 详细日志列表 (最近1000条)
            log_key = f"werss:env_exception:logs"
            log_data = {
                "url": url,
                "mp_name": mp_name,
                "mp_id": mp_id,
                "timestamp": timestamp
            }
            pipe.lpush(log_key, str(log_data))
            pipe.ltrim(log_key, 0, 999)  # 只保留最近1000条
            pipe.expire(log_key, 86400 * 7)  # 保留7天
            
            # 执行事务
            pipe.execute()
            
            return True
            
        except redis.exceptions.ConnectionError as e:
            print_error(f"Redis连接断开，记录失败: {e}")
            self._client = None
            return False
        except Exception as e:
            print_error(f"记录环境异常统计失败: {e}")
            return False
    
    def get_env_exception_stats(self, date: Optional[str] = None) -> Dict[str, Any]:
        """获取环境异常统计信息
        
        Args:
            date: 日期，格式为 YYYY-MM-DD，默认为今天
            
        Returns:
            统计信息字典
        """
        # 默认返回值
        default_stats = {
            "date": date or datetime.now().strftime("%Y-%m-%d"),
            "total": 0,
            "urls": {},
            "mp_stats": {},
            "recent_logs": []
        }
        
        if not self.is_connected:
            print_warning("Redis未连接，返回默认统计信息")
            return default_stats
            
        try:
            if date is None:
                date = datetime.now().strftime("%Y-%m-%d")
                
            # 获取总计数
            total = self._client.get(f"werss:env_exception:total:{date}")
            total = int(total) if total else 0
            
            # 获取URL列表
            url_key = f"werss:env_exception:url:{date}"
            urls = self._client.hgetall(url_key) or {}
            
            # 获取公众号统计
            mp_key = f"werss:env_exception:mp:{date}"
            mp_stats = self._client.hgetall(mp_key) or {}
            
            # 获取最近日志
            logs = self._client.lrange("werss:env_exception:logs", 0, 99) or []  # 最近100条
            
            return {
                "date": date,
                "total": total,
                "urls": urls,
                "mp_stats": mp_stats,
                "recent_logs": logs
            }
            
        except redis.exceptions.ConnectionError as e:
            print_error(f"Redis连接错误: {e}")
            return default_stats
        except Exception as e:
            print_error(f"获取环境异常统计失败: {e}")
            return default_stats
    
    def clear_env_exception(self, mp_id: str = "", url: str = "") -> bool:
        """清除环境异常记录
        
        当公众号采集成功后，清除该公众号相关的异常记录
        
        Args:
            mp_id: 公众号ID，清除该公众号的所有异常记录
            url: 文章URL，清除该URL的异常记录
            
        Returns:
            是否清除成功
        """
        if not self.is_connected:
            if not self.reconnect():
                return False
        
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            # 使用Redis事务确保原子性
            pipe = self._client.pipeline()
            
            # 清除公众号维度的异常统计
            if mp_id:
                mp_key = f"werss:env_exception:mp:{today}"
                # 获取该公众号的异常次数
                count = self._client.hget(mp_key, mp_id)
                if count:
                    count = int(count)
                    # 减少总计数
                    total_key = f"werss:env_exception:total:{today}"
                    pipe.decrby(total_key, count)
                    # 删除该公众号的统计
                    pipe.hdel(mp_key, mp_id)
                    print_info(f"已清除公众号 {mp_id} 的 {count} 条异常记录")
            
            # 清除URL维度的异常记录
            if url:
                url_key = f"werss:env_exception:url:{today}"
                if self._client.hexists(url_key, url):
                    pipe.hdel(url_key, url)
                    # 减少总计数
                    total_key = f"werss:env_exception:total:{today}"
                    pipe.decr(total_key)
                    print_info(f"已清除URL {url} 的异常记录")
            
            # 执行事务
            if pipe.command_stack:
                pipe.execute()
            
            return True
            
        except redis.exceptions.ConnectionError as e:
            print_error(f"Redis连接断开，清除失败: {e}")
            self._client = None
            return False
        except Exception as e:
            print_error(f"清除环境异常记录失败: {e}")
            return False


class RedisCache:
    """Redis 缓存工具类
    
    提供通用的键值缓存功能，支持 JSON 序列化
    """
    
    def __init__(self, key_prefix: str = "werss:cache"):
        """初始化缓存
        
        Args:
            key_prefix: 键前缀，用于区分不同模块的缓存
        """
        self.key_prefix = key_prefix
        self._client = None
    
    def _get_client(self):
        """获取 Redis 客户端"""
        if self._client is not None:
            return self._client
        
        # 复用全局 RedisClient 的连接
        if redis_client.is_connected:
            self._client = redis_client._client
            return self._client
        
        # 尝试重新连接
        if redis_client.reconnect():
            self._client = redis_client._client
            return self._client
        
        return None
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值
        
        Args:
            key: 缓存键（不含前缀）
            
        Returns:
            缓存值，不存在或出错返回 None
        """
        client = self._get_client()
        if not client:
            return None
        
        try:
            full_key = f"{self.key_prefix}:{key}"
            data = client.get(full_key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print_error(f"Redis 缓存读取失败 [{key}]: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值
        
        Args:
            key: 缓存键（不含前缀）
            value: 缓存值（会被 JSON 序列化）
            ttl: 过期时间（秒），None 表示不过期
            
        Returns:
            是否设置成功
        """
        client = self._get_client()
        if not client:
            return False
        
        try:
            full_key = f"{self.key_prefix}:{key}"
            data = json.dumps(value, ensure_ascii=False)
            
            if ttl:
                client.setex(full_key, ttl, data)
            else:
                client.set(full_key, data)
            
            return True
        except Exception as e:
            print_error(f"Redis 缓存写入失败 [{key}]: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存
        
        Args:
            key: 缓存键（不含前缀）
            
        Returns:
            是否删除成功
        """
        client = self._get_client()
        if not client:
            return False
        
        try:
            full_key = f"{self.key_prefix}:{key}"
            client.delete(full_key)
            return True
        except Exception as e:
            print_error(f"Redis 缓存删除失败 [{key}]: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """检查缓存是否存在
        
        Args:
            key: 缓存键（不含前缀）
            
        Returns:
            是否存在
        """
        client = self._get_client()
        if not client:
            return False
        
        try:
            full_key = f"{self.key_prefix}:{key}"
            return client.exists(full_key) > 0
        except Exception as e:
            print_error(f"Redis 缓存检查失败 [{key}]: {e}")
            return False
    
    def get_or_set(self, key: str, getter: callable, ttl: Optional[int] = None) -> Any:
        """获取缓存，不存在则调用 getter 函数获取并缓存
        
        Args:
            key: 缓存键
            getter: 获取数据的函数
            ttl: 过期时间（秒）
            
        Returns:
            缓存值或 getter 返回值
        """
        # 先尝试从缓存获取
        value = self.get(key)
        if value is not None:
            return value
        
        # 调用 getter 获取数据
        value = getter()
        if value is not None:
            self.set(key, value, ttl)
        
        return value
    
    @property
    def is_available(self) -> bool:
        """检查 Redis 是否可用"""
        return self._get_client() is not None


# 全局单例实例
redis_client = RedisClient()


def record_env_exception(url: str, mp_name: str = "", mp_id: str = "") -> bool:
    """记录环境异常统计（便捷函数）
    
    Args:
        url: 文章URL
        mp_name: 公众号名称
        mp_id: 公众号ID
        
    Returns:
        是否记录成功
    """
    return redis_client.record_env_exception(url, mp_name, mp_id)


def get_env_exception_stats(date: Optional[str] = None) -> Dict[str, Any]:
    """获取环境异常统计信息（便捷函数）
    
    Args:
        date: 日期，格式为 YYYY-MM-DD，默认为今天
        
    Returns:
        统计信息字典
    """
    return redis_client.get_env_exception_stats(date)


def clear_env_exception(mp_id: str = "", url: str = "") -> bool:
    """清除环境异常记录（便捷函数）
    
    当公众号采集成功后，清除该公众号相关的异常记录
    
    Args:
        mp_id: 公众号ID，清除该公众号的所有异常记录
        url: 文章URL，清除该URL的异常记录
        
    Returns:
        是否清除成功
    """
    return redis_client.clear_env_exception(mp_id, url)
