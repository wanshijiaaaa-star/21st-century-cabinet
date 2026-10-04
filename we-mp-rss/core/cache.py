import os
import hashlib
import time
import json
import pickle
from typing import Any, Optional, Union
from functools import wraps
from core.config import cfg

class ViewCache:
    """视图缓存管理类"""
    
    def __init__(self, cache_dir: str = None, default_ttl: int = 1800, enabled: bool = False):
        self.cache_dir = cache_dir or cfg.get("cache.views.dir", "data/cache/views")
        self.default_ttl = default_ttl or cfg.get("cache.views.ttl", 1800)  # 默认30分钟
        self.enabled = enabled or cfg.get("cache.views.enabled", False)
        
        # 确保缓存目录存在
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_cache_key(self, prefix: str, **kwargs) -> str:
        """生成缓存键"""
        # 过滤掉不需要包含在缓存键中的参数
        filter_keys = {'request'}
        filtered_kwargs = {k: v for k, v in kwargs.items() if k not in filter_keys}
        
        # 将参数转换为可哈希的字符串
        key_data = json.dumps(filtered_kwargs, sort_keys=True, default=str)
        key_hash = hashlib.sha256(key_data.encode('utf-8')).hexdigest()
        return f"{prefix}_{key_hash}"
    
    def _get_cache_path(self, cache_key: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, f"{cache_key}.cache")
    
    def get(self, prefix: str, ttl: Optional[int] = None, **kwargs) -> Optional[Any]:
        """获取缓存数据"""
        if not self.enabled:
            return None
            
        cache_key = self._get_cache_key(prefix, **kwargs)
        cache_path = self._get_cache_path(cache_key)
        
        if not os.path.exists(cache_path):
            return None
        
        # 检查缓存是否过期
        ttl = ttl or self.default_ttl
        file_mtime = os.path.getmtime(cache_path)
        if time.time() - file_mtime > ttl:
            # 删除过期缓存
            try:
                os.remove(cache_path)
            except OSError:
                pass
            return None
        
        # 读取缓存数据
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except (pickle.PickleError, IOError, EOFError):
            # 缓存文件损坏，删除并返回None
            try:
                os.remove(cache_path)
            except OSError:
                pass
            return None
    
    def set(self, prefix: str, data: Any, **kwargs) -> bool:
        """设置缓存数据"""
        if not self.enabled:
            return True
            
        cache_key = self._get_cache_key(prefix, **kwargs)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
            return True
        except (pickle.PickleError, IOError):
            return False
    
    def clear(self, prefix: Optional[str] = None) -> bool:
        """清除缓存"""
        try:
            if prefix:
                # 清除特定前缀的缓存
                for filename in os.listdir(self.cache_dir):
                    if filename.startswith(f"{prefix}_") and filename.endswith('.cache'):
                        os.remove(os.path.join(self.cache_dir, filename))
            else:
                # 清除所有缓存
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith('.cache'):
                        os.remove(os.path.join(self.cache_dir, filename))
            return True
        except OSError:
            return False
    
    def delete_pattern(self, pattern: str) -> bool:
        """删除匹配模式的缓存"""
        try:
            import glob
            pattern_path = os.path.join(self.cache_dir, f"{pattern}_*.cache")
            for cache_file in glob.glob(pattern_path):
                os.remove(cache_file)
            return True
        except OSError:
            return False

# 全局缓存实例
view_cache = ViewCache()
data_cache = ViewCache("data/cache/data", default_ttl=3600, enabled=True)  # 数据缓存，默认1小时

def cache_view(prefix: str, ttl: Optional[int] = None, key_func=None):
    """
    视图缓存装饰器
    
    Args:
        prefix: 缓存前缀
        ttl: 缓存过期时间（秒），None表示使用默认值
        key_func: 自定义缓存键生成函数，接收函数参数，返回字符串
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 如果禁用缓存，直接执行原函数
            if not view_cache.enabled:
                return await func(*args, **kwargs)
            
            # 生成缓存键
            if key_func:
                cache_key_prefix = key_func(*args, **kwargs)
            else:
                cache_key_prefix = prefix
            
            # 尝试从缓存获取
            cached_result = view_cache.get(cache_key_prefix, ttl=ttl, **kwargs)
            if cached_result is not None:
                return cached_result
            
            # 执行原函数
            result = await func(*args, **kwargs)
            
            # 缓存结果
            view_cache.set(cache_key_prefix, result, **kwargs)
            
            return result
        return wrapper
    return decorator

def clear_cache_pattern(pattern: str) -> bool:
    """清除匹配模式的缓存"""
    return view_cache.delete_pattern(pattern)

def clear_all_cache() -> bool:
    """清除所有视图缓存"""
    return view_cache.clear()