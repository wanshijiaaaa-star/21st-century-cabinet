#!/usr/bin/env python3
"""
轻量级 Redis 服务端实现
支持基本的 Redis 协议 (RESP) 和常用命令

使用方法:
    python redis_server.py --port 6379 --max-memory 128
    python redis_server.py --config ../config.yaml

支持命令:
    键值操作: SET, GET, DEL, EXISTS, KEYS, TTL, EXPIRE, EXPIREAT,
              PEXPIRE, PEXPIREAT, PERSIST, PTTL, TYPE
              MGET, MSET, MSETNX, SETNX, SETEX, GETSET
    计数器:   INCR, DECR, INCRBY, DECRBY, INCRBYFLOAT
    List:     LPUSH, RPUSH, LPOP, RPOP, LLEN, LRANGE, LTRIM,
              LINDEX, LSET, RPOPLPUSH, BLPOP, BRPOP
    Hash:     HSET, HMSET, HMGET, HGET, HGETALL, HDEL, HEXISTS,
              HKEYS, HVALS, HLEN, HINCRBY, HINCRBYFLOAT, HSETNX
    Set:      SADD, SREM, SMEMBERS, SISMEMBER, SCARD
    服务器:   PING, ECHO, AUTH, INFO, DBSIZE, FLUSHDB, FLUSHALL,
              SAVE, QUIT, SHUTDOWN, COMMAND, CONFIG
"""

import socket
import threading
import time
import argparse
import json
import os
import yaml
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime
from collections import OrderedDict
import signal
import sys


class RedisError(Exception):
    """Redis 错误异常"""
    pass


class RESPParser:
    """Redis 序列化协议 (RESP) 解析器"""
    
    CRLF = b'\r\n'
    
    @staticmethod
    def parse(data: bytes) -> Tuple[Any, int]:
        """解析 RESP 数据，返回 (值, 消耗的字节数)"""
        if not data:
            return None, 0
        
        type_byte = chr(data[0])
        
        if type_byte == '+':  # Simple String
            end = data.find(RESPParser.CRLF)
            if end == -1:
                return None, 0
            return data[1:end].decode('utf-8'), end + 2
        
        elif type_byte == '-':  # Error
            end = data.find(RESPParser.CRLF)
            if end == -1:
                return None, 0
            return RedisError(data[1:end].decode('utf-8')), end + 2
        
        elif type_byte == ':':  # Integer
            end = data.find(RESPParser.CRLF)
            if end == -1:
                return None, 0
            return int(data[1:end]), end + 2
        
        elif type_byte == '$':  # Bulk String
            end = data.find(RESPParser.CRLF)
            if end == -1:
                return None, 0
            length = int(data[1:end])
            if length == -1:
                return None, end + 2
            start = end + 2
            return data[start:start + length].decode('utf-8'), start + length + 2
        
        elif type_byte == '*':  # Array
            end = data.find(RESPParser.CRLF)
            if end == -1:
                return None, 0
            count = int(data[1:end])
            if count == -1:
                return None, end + 2
            
            items = []
            offset = end + 2
            for _ in range(count):
                item, consumed = RESPParser.parse(data[offset:])
                if consumed == 0:
                    return None, 0
                items.append(item)
                offset += consumed
            return items, offset
        
        else:
            # 内联命令 (兼容模式)
            end = data.find(RESPParser.CRLF)
            if end == -1:
                return None, 0
            line = data[:end].decode('utf-8')
            return line.split(), end + 2
    
    @staticmethod
    def encode(value: Any) -> bytes:
        """将值编码为 RESP 格式"""
        if value is None:
            return b'$-1\r\n'
        elif isinstance(value, bool):
            return f':{1 if value else 0}\r\n'.encode()
        elif isinstance(value, int):
            return f':{value}\r\n'.encode()
        elif isinstance(value, RedisError):
            return f'-{str(value)}\r\n'.encode()
        elif isinstance(value, str):
            encoded = value.encode('utf-8')
            return f'${len(encoded)}\r\n'.encode() + encoded + b'\r\n'
        elif isinstance(value, (list, tuple)):
            result = f'*{len(value)}\r\n'.encode()
            for item in value:
                result += RESPParser.encode(item)
            return result
        elif isinstance(value, dict):
            result = f'*{len(value) * 2}\r\n'.encode()
            for k, v in value.items():
                result += RESPParser.encode(k)
                result += RESPParser.encode(v)
            return result
        elif isinstance(value, bytes):
            return f'${len(value)}\r\n'.encode() + value + b'\r\n'
        else:
            return RESPParser.encode(str(value))


class MemoryStore:
    """内存数据存储"""
    
    def __init__(self, max_memory_mb: int = 128, persist_file: Optional[str] = None):
        self.data: Dict[str, Any] = {}
        self.expires: Dict[str, float] = {}
        self.max_memory = max_memory_mb * 1024 * 1024
        self.current_memory = 0
        self.lock = threading.RLock()
        self.persist_file = persist_file  # 持久化文件路径
        
        # 数据结构类型
        self.type_map: Dict[str, str] = {}  # key -> type (string, list, hash, set)
    
    def _check_memory(self, size: int = 0) -> bool:
        """检查内存限制"""
        return self.current_memory + size <= self.max_memory
    
    def _evict_if_needed(self):
        """LRU 淘汰策略"""
        while self.current_memory > self.max_memory * 0.9 and self.data:
            # 简单 LRU: 删除最早过期的 key 或随机 key
            if self.expires:
                oldest_key = min(self.expires.keys(), key=lambda k: self.expires[k])
                self._delete_key(oldest_key)
            else:
                # 随机删除一个
                key = next(iter(self.data))
                self._delete_key(key)
    
    def _estimate_size(self, value: Any) -> int:
        """估算值占用内存大小"""
        if value is None:
            return 0
        elif isinstance(value, str):
            return len(value.encode('utf-8')) + 32
        elif isinstance(value, (list, tuple)):
            return sum(self._estimate_size(v) for v in value) + 64
        elif isinstance(value, dict):
            return sum(self._estimate_size(k) + self._estimate_size(v) for k, v in value.items()) + 64
        elif isinstance(value, set):
            return sum(self._estimate_size(v) for v in value) + 64
        else:
            return 32
    
    def _delete_key(self, key: str):
        """删除 key 并更新内存统计"""
        if key in self.data:
            self.current_memory -= self._estimate_size(self.data[key])
            del self.data[key]
            self.type_map.pop(key, None)
        self.expires.pop(key, None)
    
    def is_expired(self, key: str) -> bool:
        """检查 key 是否过期"""
        if key in self.expires:
            if time.time() > self.expires[key]:
                self._delete_key(key)
                return True
        return False
    
    def cleanup_expired(self):
        """清理过期 key"""
        now = time.time()
        expired_keys = [k for k, exp in self.expires.items() if now > exp]
        for key in expired_keys:
            self._delete_key(key)
    
    def get(self, key: str) -> Optional[Any]:
        if self.is_expired(key):
            return None
        return self.data.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        with self.lock:
            # 删除旧值
            if key in self.data:
                self._delete_key(key)
            
            # 检查内存
            size = self._estimate_size(value)
            if not self._check_memory(size):
                self._evict_if_needed()
                if not self._check_memory(size):
                    return False
            
            self.data[key] = value
            self.current_memory += size
            self.type_map[key] = 'string'
            
            if ttl:
                self.expires[key] = time.time() + ttl
            
            # 自动保存到文件
            if self.persist_file:
                self._auto_save()
            
            return True
    
    def delete(self, *keys) -> int:
        with self.lock:
            count = 0
            for key in keys:
                if key in self.data:
                    self._delete_key(key)
                    count += 1
            return count
    
    def exists(self, *keys) -> int:
        count = 0
        for key in keys:
            if not self.is_expired(key) and key in self.data:
                count += 1
        return count
    
    def keys(self, pattern: str = '*') -> List[str]:
        import fnmatch
        result = []
        for key in list(self.data.keys()):
            if not self.is_expired(key):
                if fnmatch.fnmatch(key, pattern):
                    result.append(key)
        return result
    
    def set_ttl(self, key: str, ttl: int) -> bool:
        if self.is_expired(key) or key not in self.data:
            return False
        self.expires[key] = time.time() + ttl
        return True
    
    def get_ttl(self, key: str) -> int:
        if key not in self.data:
            return -2
        if self.is_expired(key):
            return -2
        if key not in self.expires:
            return -1
        return int(self.expires[key] - time.time())
    
    # List 操作
    def lpush(self, key: str, *values) -> int:
        with self.lock:
            if key not in self.data:
                self.data[key] = list(values)
                self.type_map[key] = 'list'
            elif self.type_map.get(key) != 'list':
                raise RedisError("WRONGTYPE Operation against a key holding the wrong kind of value")
            else:
                self.data[key] = list(values) + self.data[key]
            return len(self.data[key])
    
    def rpush(self, key: str, *values) -> int:
        with self.lock:
            if key not in self.data:
                self.data[key] = list(values)
                self.type_map[key] = 'list'
            elif self.type_map.get(key) != 'list':
                raise RedisError("WRONGTYPE Operation against a key holding the wrong kind of value")
            else:
                self.data[key].extend(values)
            return len(self.data[key])
    
    def lpop(self, key: str) -> Optional[Any]:
        with self.lock:
            if key not in self.data or self.type_map.get(key) != 'list':
                return None
            if self.data[key]:
                return self.data[key].pop(0)
            return None
    
    def rpop(self, key: str) -> Optional[Any]:
        with self.lock:
            if key not in self.data or self.type_map.get(key) != 'list':
                return None
            if self.data[key]:
                return self.data[key].pop()
            return None
    
    def llen(self, key: str) -> int:
        if self.is_expired(key) or key not in self.data:
            return 0
        if self.type_map.get(key) != 'list':
            raise RedisError("WRONGTYPE Operation against a key holding the wrong kind of value")
        return len(self.data.get(key, []))
    
    def lrange(self, key: str, start: int, end: int) -> List[Any]:
        if self.is_expired(key) or key not in self.data:
            return []
        if self.type_map.get(key) != 'list':
            raise RedisError("WRONGTYPE Operation against a key holding the wrong kind of value")
        lst = self.data[key]
        if end == -1:
            return lst[start:]
        return lst[start:end + 1]
    
    def ltrim(self, key: str, start: int, end: int) -> bool:
        """裁剪列表，只保留指定范围内的元素"""
        with self.lock:
            if self.is_expired(key) or key not in self.data:
                return True
            if self.type_map.get(key) != 'list':
                raise RedisError("WRONGTYPE Operation against a key holding the wrong kind of value")
            
            lst = self.data[key]
            length = len(lst)
            
            # 处理负索引
            if start < 0:
                start = max(0, length + start)
            if end < 0:
                end = length + end
            
            if start > end or start >= length:
                self.data[key] = []
            else:
                end = min(end, length - 1)
                self.data[key] = lst[start:end + 1]
            
            return True
    
    def lindex(self, key: str, index: int) -> Optional[Any]:
        """获取列表指定索引的元素"""
        if self.is_expired(key) or key not in self.data:
            return None
        if self.type_map.get(key) != 'list':
            raise RedisError("WRONGTYPE Operation against a key holding the wrong kind of value")
        
        lst = self.data[key]
        length = len(lst)
        
        # 处理负索引
        if index < 0:
            index = length + index
        
        if index < 0 or index >= length:
            return None
        return lst[index]
    
    def lset(self, key: str, index: int, value: Any) -> bool:
        """设置列表指定索引的元素"""
        with self.lock:
            if self.is_expired(key) or key not in self.data:
                raise RedisError("no such key")
            if self.type_map.get(key) != 'list':
                raise RedisError("WRONGTYPE Operation against a key holding the wrong kind of value")
            
            lst = self.data[key]
            length = len(lst)
            
            # 处理负索引
            if index < 0:
                index = length + index
            
            if index < 0 or index >= length:
                raise RedisError("index out of range")
            
            lst[index] = value
            return True
    
    # Hash 操作
    def hset(self, key: str, field: str = None, value: Any = None, mapping: dict = None) -> int:
        """设置哈希字段，支持单字段和多字段"""
        with self.lock:
            if key not in self.data:
                self.data[key] = {}
                self.type_map[key] = 'hash'
            elif self.type_map.get(key) != 'hash':
                raise RedisError("WRONGTYPE Operation against a key holding the wrong kind of value")
            
            count = 0
            # 支持多字段设置
            if mapping:
                for f, v in mapping.items():
                    if f not in self.data[key]:
                        count += 1
                    self.data[key][f] = v
            elif field is not None:
                is_new = field not in self.data[key]
                self.data[key][field] = value
                count = 1 if is_new else 0
            
            return count
    
    def hmset(self, key: str, mapping: dict) -> bool:
        """批量设置哈希字段"""
        self.hset(key=key, mapping=mapping)
        return True
    
    def hmget(self, key: str, *fields) -> List[Optional[Any]]:
        """批量获取哈希字段"""
        if self.is_expired(key) or key not in self.data:
            return [None] * len(fields)
        if self.type_map.get(key) != 'hash':
            raise RedisError("WRONGTYPE Operation against a key holding the wrong kind of value")
        return [self.data[key].get(f) for f in fields]
    
    def hlen(self, key: str) -> int:
        """获取哈希字段数量"""
        if self.is_expired(key) or key not in self.data:
            return 0
        if self.type_map.get(key) != 'hash':
            raise RedisError("WRONGTYPE Operation against a key holding the wrong kind of value")
        return len(self.data[key])
    
    def hincrby(self, key: str, field: str, increment: int = 1) -> int:
        """哈希字段增量"""
        with self.lock:
            if key not in self.data:
                self.data[key] = {}
                self.type_map[key] = 'hash'
            elif self.type_map.get(key) != 'hash':
                raise RedisError("WRONGTYPE Operation against a key holding the wrong kind of value")
            
            value = self.data[key].get(field, '0')
            try:
                value = int(value)
            except (ValueError, TypeError):
                raise RedisError("value is not an integer or out of range")
            
            new_value = value + increment
            self.data[key][field] = str(new_value)
            return new_value
    
    def hincrbyfloat(self, key: str, field: str, increment: float) -> str:
        """哈希字段浮点增量"""
        with self.lock:
            if key not in self.data:
                self.data[key] = {}
                self.type_map[key] = 'hash'
            elif self.type_map.get(key) != 'hash':
                raise RedisError("WRONGTYPE Operation against a key holding the wrong kind of value")
            
            value = self.data[key].get(field, '0')
            try:
                value = float(value)
            except (ValueError, TypeError):
                raise RedisError("value is not a valid float")
            
            new_value = value + increment
            result = str(new_value)
            self.data[key][field] = result
            return result
    
    def hsetnx(self, key: str, field: str, value: Any) -> bool:
        """仅当字段不存在时设置"""
        with self.lock:
            if key not in self.data:
                self.data[key] = {}
                self.type_map[key] = 'hash'
            elif self.type_map.get(key) != 'hash':
                raise RedisError("WRONGTYPE Operation against a key holding the wrong kind of value")
            
            if field in self.data[key]:
                return False
            self.data[key][field] = value
            return True
    
    def hget(self, key: str, field: str) -> Optional[Any]:
        if self.is_expired(key) or key not in self.data:
            return None
        if self.type_map.get(key) != 'hash':
            raise RedisError("WRONGTYPE Operation against a key holding the wrong kind of value")
        return self.data[key].get(field)
    
    def hgetall(self, key: str) -> Dict[str, Any]:
        if self.is_expired(key) or key not in self.data:
            return {}
        if self.type_map.get(key) != 'hash':
            raise RedisError("WRONGTYPE Operation against a key holding the wrong kind of value")
        return self.data[key]
    
    def hdel(self, key: str, *fields) -> int:
        with self.lock:
            if key not in self.data:
                return 0
            if self.type_map.get(key) != 'hash':
                raise RedisError("WRONGTYPE Operation against a key holding the wrong kind of value")
            count = 0
            for f in fields:
                if f in self.data[key]:
                    del self.data[key][f]
                    count += 1
            return count
    
    def hexists(self, key: str, field: str) -> bool:
        if self.is_expired(key) or key not in self.data:
            return False
        if self.type_map.get(key) != 'hash':
            raise RedisError("WRONGTYPE Operation against a key holding the wrong kind of value")
        return field in self.data[key]
    
    def hkeys(self, key: str) -> List[str]:
        if self.is_expired(key) or key not in self.data:
            return []
        if self.type_map.get(key) != 'hash':
            raise RedisError("WRONGTYPE Operation against a key holding the wrong kind of value")
        return list(self.data[key].keys())
    
    def hvals(self, key: str) -> List[Any]:
        if self.is_expired(key) or key not in self.data:
            return []
        if self.type_map.get(key) != 'hash':
            raise RedisError("WRONGTYPE Operation against a key holding the wrong kind of value")
        return list(self.data[key].values())
    
    # Set 操作
    def sadd(self, key: str, *members) -> int:
        with self.lock:
            if key not in self.data:
                self.data[key] = set()
                self.type_map[key] = 'set'
            elif self.type_map.get(key) != 'set':
                raise RedisError("WRONGTYPE Operation against a key holding the wrong kind of value")
            
            count = 0
            for m in members:
                if m not in self.data[key]:
                    self.data[key].add(m)
                    count += 1
            return count
    
    def srem(self, key: str, *members) -> int:
        with self.lock:
            if key not in self.data:
                return 0
            if self.type_map.get(key) != 'set':
                raise RedisError("WRONGTYPE Operation against a key holding the wrong kind of value")
            
            count = 0
            for m in members:
                if m in self.data[key]:
                    self.data[key].remove(m)
                    count += 1
            return count
    
    def smembers(self, key: str) -> set:
        if self.is_expired(key) or key not in self.data:
            return set()
        if self.type_map.get(key) != 'set':
            raise RedisError("WRONGTYPE Operation against a key holding the wrong kind of value")
        return self.data[key]
    
    def sismember(self, key: str, member: str) -> bool:
        if self.is_expired(key) or key not in self.data:
            return False
        if self.type_map.get(key) != 'set':
            raise RedisError("WRONGTYPE Operation against a key holding the wrong kind of value")
        return member in self.data[key]
    
    def scard(self, key: str) -> int:
        if self.is_expired(key) or key not in self.data:
            return 0
        if self.type_map.get(key) != 'set':
            raise RedisError("WRONGTYPE Operation against a key holding the wrong kind of value")
        return len(self.data[key])
    
    # 计数器操作
    def incr(self, key: str) -> int:
        with self.lock:
            value = self.get(key)
            if value is None:
                value = 0
            elif not isinstance(value, (int, str)) or (isinstance(value, str) and not value.lstrip('-').isdigit()):
                raise RedisError("value is not an integer or out of range")
            else:
                value = int(value)
            
            new_value = value + 1
            self.set(key, str(new_value))
            return new_value
    
    def decr(self, key: str) -> int:
        with self.lock:
            value = self.get(key)
            if value is None:
                value = 0
            elif not isinstance(value, (int, str)) or (isinstance(value, str) and not value.lstrip('-').isdigit()):
                raise RedisError("value is not an integer or out of range")
            else:
                value = int(value)
            
            new_value = value - 1
            self.set(key, str(new_value))
            return new_value
    
    def incrby(self, key: str, increment: int) -> int:
        with self.lock:
            value = self.get(key)
            if value is None:
                value = 0
            elif not isinstance(value, (int, str)) or (isinstance(value, str) and not value.lstrip('-').isdigit()):
                raise RedisError("value is not an integer or out of range")
            else:
                value = int(value)
            
            new_value = value + increment
            self.set(key, str(new_value))
            return new_value
    
    def flushdb(self):
        """清空当前数据库"""
        with self.lock:
            self.data.clear()
            self.expires.clear()
            self.type_map.clear()
            self.current_memory = 0
    
    def save(self, filepath: str):
        """保存数据到文件"""
        with self.lock:
            data = {
                'data': self.data,
                'expires': self.expires,
                'type_map': self.type_map
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, default=str)
    
    def _auto_save(self):
        """自动保存数据到文件（内部方法）"""
        try:
            if self.persist_file:
                os.makedirs(os.path.dirname(self.persist_file), exist_ok=True)
                data = {
                    'data': self.data,
                    'expires': self.expires,
                    'type_map': self.type_map
                }
                with open(self.persist_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"[WARN] 自动保存数据失败: {e}")
    
    def load(self, filepath: str):
        """从文件加载数据"""
        if os.path.exists(filepath):
            with self.lock:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.data = data.get('data', {})
                    self.expires = data.get('expires', {})
                    self.type_map = data.get('type_map', {})
                    
                    # 转换 expires 中的字符串时间为浮点数
                    self.expires = {k: float(v) for k, v in self.expires.items()}


class RedisServer:
    """Redis 服务端"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 6379, 
                 max_memory_mb: int = 128, password: Optional[str] = None):
        self.host = host
        self.port = port
        self.password = password
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'redis')
        self.rdb_file = os.path.join(self.data_dir, 'dump.rdb')
        self.store = MemoryStore(max_memory_mb, persist_file=self.rdb_file)
        self.running = False
        self.server_socket = None
        self.clients = []
        self.start_time = time.time()
        
        # 统计
        self.stats = {
            'total_connections': 0,
            'total_commands': 0,
            'total_bytes_read': 0,
            'total_bytes_written': 0
        }
        
        # 加载持久化数据
        self._load_data()
    
    def _load_data(self):
        """加载持久化数据"""
        try:
            if os.path.exists(self.rdb_file):
                self.store.load(self.rdb_file)
                print(f"[INFO] 加载持久化数据成功: {self.rdb_file}")
        except Exception as e:
            print(f"[WARN] 加载持久化数据失败: {e}")
    
    def _save_data(self):
        """保存持久化数据"""
        try:
            os.makedirs(os.path.dirname(self.rdb_file), exist_ok=True)
            self.store.save(self.rdb_file)
            print(f"[INFO] 保存持久化数据成功: {self.rdb_file}")
        except Exception as e:
            print(f"[ERROR] 保存持久化数据失败: {e}")
    
    def handle_command(self, command: List[str], authenticated: bool = False) -> Any:
        """处理 Redis 命令"""
        if not command:
            return RedisError("empty command")
        
        cmd = command[0].upper()
        args = command[1:]
        self.stats['total_commands'] += 1
        
        # 认证检查 - 如果服务端设置了密码且客户端未认证，则拒绝除 AUTH 外的所有命令
        if self.password and not authenticated and cmd != 'AUTH':
            return RedisError("NOAUTH Authentication required")
        
        # 基础命令
        if cmd == 'PING':
            if len(args) == 0:
                return 'PONG'
            return args[0]
        
        elif cmd == 'ECHO':
            if len(args) < 1:
                return RedisError("wrong number of arguments for 'echo' command")
            return args[0]
        
        elif cmd == 'AUTH':
            if len(args) < 1:
                return RedisError("wrong number of arguments for 'auth' command")
            if args[0] == self.password:
                return 'OK'
            return RedisError("ERR invalid password")
        
        # 键值操作
        elif cmd == 'SET':
            if len(args) < 2:
                return RedisError("wrong number of arguments for 'set' command")
            key, value = args[0], args[1]
            ttl = None
            if len(args) >= 4 and args[2].upper() == 'EX':
                ttl = int(args[3])
            elif len(args) >= 4 and args[2].upper() == 'PX':
                ttl = int(args[3]) // 1000
            self.store.set(key, value, ttl)
            return 'OK'
        
        elif cmd == 'GET':
            if len(args) < 1:
                return RedisError("wrong number of arguments for 'get' command")
            return self.store.get(args[0])
        
        elif cmd == 'DEL':
            if len(args) < 1:
                return RedisError("wrong number of arguments for 'del' command")
            return self.store.delete(*args)
        
        elif cmd == 'EXISTS':
            if len(args) < 1:
                return RedisError("wrong number of arguments for 'exists' command")
            return self.store.exists(*args)
        
        elif cmd == 'KEYS':
            pattern = args[0] if args else '*'
            return self.store.keys(pattern)
        
        elif cmd == 'TTL':
            if len(args) < 1:
                return RedisError("wrong number of arguments for 'ttl' command")
            return self.store.get_ttl(args[0])
        
        elif cmd == 'EXPIRE':
            if len(args) < 2:
                return RedisError("wrong number of arguments for 'expire' command")
            return 1 if self.store.set_ttl(args[0], int(args[1])) else 0
        
        elif cmd == 'EXPIREAT':
            if len(args) < 2:
                return RedisError("wrong number of arguments for 'expireat' command")
            ttl = int(args[1]) - int(time.time())
            return 1 if self.store.set_ttl(args[0], ttl) else 0
        
        elif cmd == 'PEXPIRE':
            if len(args) < 2:
                return RedisError("wrong number of arguments for 'pexpire' command")
            return 1 if self.store.set_ttl(args[0], int(args[1]) // 1000) else 0
        
        elif cmd == 'PEXPIREAT':
            if len(args) < 2:
                return RedisError("wrong number of arguments for 'pexpireat' command")
            ttl = (int(args[1]) // 1000) - int(time.time())
            return 1 if self.store.set_ttl(args[0], ttl) else 0
        
        elif cmd == 'PERSIST':
            if len(args) < 1:
                return RedisError("wrong number of arguments for 'persist' command")
            if args[0] in self.store.expires:
                del self.store.expires[args[0]]
                return 1
            return 0
        
        elif cmd == 'PTTL':
            if len(args) < 1:
                return RedisError("wrong number of arguments for 'pttl' command")
            ttl = self.store.get_ttl(args[0])
            if ttl == -1:
                return -1
            if ttl == -2:
                return -2
            return ttl * 1000
        
        elif cmd == 'MGET':
            if len(args) < 1:
                return RedisError("wrong number of arguments for 'mget' command")
            return [self.store.get(k) for k in args]
        
        elif cmd == 'MSET':
            if len(args) < 2 or len(args) % 2 != 0:
                return RedisError("wrong number of arguments for 'mset' command")
            i = 0
            while i < len(args):
                self.store.set(args[i], args[i + 1])
                i += 2
            return 'OK'
        
        elif cmd == 'MSETNX':
            if len(args) < 2 or len(args) % 2 != 0:
                return RedisError("wrong number of arguments for 'msetnx' command")
            # 检查是否有已存在的 key
            for i in range(0, len(args), 2):
                if args[i] in self.store.data and not self.store.is_expired(args[i]):
                    return 0
            # 设置所有 key
            i = 0
            while i < len(args):
                self.store.set(args[i], args[i + 1])
                i += 2
            return 1
        
        elif cmd == 'SETNX':
            if len(args) < 2:
                return RedisError("wrong number of arguments for 'setnx' command")
            if args[0] in self.store.data and not self.store.is_expired(args[0]):
                return 0
            self.store.set(args[0], args[1])
            return 1
        
        elif cmd == 'SETEX':
            if len(args) < 3:
                return RedisError("wrong number of arguments for 'setex' command")
            self.store.set(args[0], args[2], int(args[1]))
            return 'OK'
        
        elif cmd == 'GETSET':
            if len(args) < 2:
                return RedisError("wrong number of arguments for 'getset' command")
            old_value = self.store.get(args[0])
            self.store.set(args[0], args[1])
            return old_value
        
        elif cmd == 'INCRBY':
            if len(args) < 2:
                return RedisError("wrong number of arguments for 'incrby' command")
            return self.store.incrby(args[0], int(args[1]))
        
        elif cmd == 'DECRBY':
            if len(args) < 2:
                return RedisError("wrong number of arguments for 'decrby' command")
            return self.store.incrby(args[0], -int(args[1]))
        
        elif cmd == 'INCRBYFLOAT':
            if len(args) < 2:
                return RedisError("wrong number of arguments for 'incrbyfloat' command")
            value = self.store.get(args[0])
            if value is None:
                value = '0'
            try:
                new_value = float(value) + float(args[1])
                self.store.set(args[0], str(new_value))
                return str(new_value)
            except (ValueError, TypeError):
                return RedisError("value is not a valid float")
        
        # 计数器
        elif cmd == 'INCR':
            if len(args) < 1:
                return RedisError("wrong number of arguments for 'incr' command")
            return self.store.incr(args[0])
        
        elif cmd == 'DECR':
            if len(args) < 1:
                return RedisError("wrong number of arguments for 'decr' command")
            return self.store.decr(args[0])
        
        elif cmd == 'TYPE':
            if len(args) < 1:
                return RedisError("wrong number of arguments for 'type' command")
            key = args[0]
            if self.store.is_expired(key) or key not in self.store.data:
                return 'none'
            return self.store.type_map.get(key, 'string')
        
        # List 操作
        elif cmd == 'LPUSH':
            if len(args) < 2:
                return RedisError("wrong number of arguments for 'lpush' command")
            return self.store.lpush(args[0], *args[1:])
        
        elif cmd == 'RPUSH':
            if len(args) < 2:
                return RedisError("wrong number of arguments for 'rpush' command")
            return self.store.rpush(args[0], *args[1:])
        
        elif cmd == 'LPOP':
            if len(args) < 1:
                return RedisError("wrong number of arguments for 'lpop' command")
            return self.store.lpop(args[0])
        
        elif cmd == 'RPOP':
            if len(args) < 1:
                return RedisError("wrong number of arguments for 'rpop' command")
            return self.store.rpop(args[0])
        
        elif cmd == 'RPOPLPUSH':
            if len(args) < 2:
                return RedisError("wrong number of arguments for 'rpoplpush' command")
            value = self.store.rpop(args[0])
            if value is not None:
                self.store.lpush(args[1], value)
            return value
        
        elif cmd == 'BLPOP':
            if len(args) < 2:
                return RedisError("wrong number of arguments for 'blpop' command")
            # 简化实现：不阻塞，直接尝试获取
            for key in args[:-1]:
                value = self.store.lpop(key)
                if value is not None:
                    return [key, value]
            return None
        
        elif cmd == 'BRPOP':
            if len(args) < 2:
                return RedisError("wrong number of arguments for 'brpop' command")
            # 简化实现：不阻塞，直接尝试获取
            for key in args[:-1]:
                value = self.store.rpop(key)
                if value is not None:
                    return [key, value]
            return None
        
        elif cmd == 'LLEN':
            if len(args) < 1:
                return RedisError("wrong number of arguments for 'llen' command")
            return self.store.llen(args[0])
        
        elif cmd == 'LRANGE':
            if len(args) < 3:
                return RedisError("wrong number of arguments for 'lrange' command")
            return self.store.lrange(args[0], int(args[1]), int(args[2]))
        
        elif cmd == 'LTRIM':
            if len(args) < 3:
                return RedisError("wrong number of arguments for 'ltrim' command")
            self.store.ltrim(args[0], int(args[1]), int(args[2]))
            return 'OK'
        
        elif cmd == 'LINDEX':
            if len(args) < 2:
                return RedisError("wrong number of arguments for 'lindex' command")
            return self.store.lindex(args[0], int(args[1]))
        
        elif cmd == 'LSET':
            if len(args) < 3:
                return RedisError("wrong number of arguments for 'lset' command")
            try:
                self.store.lset(args[0], int(args[1]), args[2])
                return 'OK'
            except RedisError as e:
                return e
        
        # Hash 操作
        elif cmd == 'HSET':
            if len(args) < 3:
                return RedisError("wrong number of arguments for 'hset' command")
            # 支持多字段: HSET key field value [field value ...]
            if len(args) == 3:
                return self.store.hset(args[0], args[1], args[2])
            else:
                # 多字段设置
                mapping = {}
                i = 1
                while i < len(args) - 1:
                    mapping[args[i]] = args[i + 1]
                    i += 2
                return self.store.hset(args[0], mapping=mapping)
        
        elif cmd == 'HMSET':
            if len(args) < 3 or len(args) % 2 == 0:
                return RedisError("wrong number of arguments for 'hmset' command")
            mapping = {}
            i = 1
            while i < len(args) - 1:
                mapping[args[i]] = args[i + 1]
                i += 2
            self.store.hmset(args[0], mapping)
            return 'OK'
        
        elif cmd == 'HMGET':
            if len(args) < 2:
                return RedisError("wrong number of arguments for 'hmget' command")
            return self.store.hmget(args[0], *args[1:])
        
        elif cmd == 'HLEN':
            if len(args) < 1:
                return RedisError("wrong number of arguments for 'hlen' command")
            return self.store.hlen(args[0])
        
        elif cmd == 'HINCRBY':
            if len(args) < 3:
                return RedisError("wrong number of arguments for 'hincrby' command")
            try:
                return self.store.hincrby(args[0], args[1], int(args[2]))
            except RedisError as e:
                return e
        
        elif cmd == 'HINCRBYFLOAT':
            if len(args) < 3:
                return RedisError("wrong number of arguments for 'hincrbyfloat' command")
            try:
                return self.store.hincrbyfloat(args[0], args[1], float(args[2]))
            except RedisError as e:
                return e
        
        elif cmd == 'HSETNX':
            if len(args) < 3:
                return RedisError("wrong number of arguments for 'hsetnx' command")
            return 1 if self.store.hsetnx(args[0], args[1], args[2]) else 0
        
        elif cmd == 'HGET':
            if len(args) < 2:
                return RedisError("wrong number of arguments for 'hget' command")
            return self.store.hget(args[0], args[1])
        
        elif cmd == 'HGETALL':
            if len(args) < 1:
                return RedisError("wrong number of arguments for 'hgetall' command")
            return self.store.hgetall(args[0])
        
        elif cmd == 'HDEL':
            if len(args) < 2:
                return RedisError("wrong number of arguments for 'hdel' command")
            return self.store.hdel(args[0], *args[1:])
        
        elif cmd == 'HEXISTS':
            if len(args) < 2:
                return RedisError("wrong number of arguments for 'hexists' command")
            return 1 if self.store.hexists(args[0], args[1]) else 0
        
        elif cmd == 'HKEYS':
            if len(args) < 1:
                return RedisError("wrong number of arguments for 'hkeys' command")
            return self.store.hkeys(args[0])
        
        elif cmd == 'HVALS':
            if len(args) < 1:
                return RedisError("wrong number of arguments for 'hvals' command")
            return self.store.hvals(args[0])
        
        # Set 操作
        elif cmd == 'SADD':
            if len(args) < 2:
                return RedisError("wrong number of arguments for 'sadd' command")
            return self.store.sadd(args[0], *args[1:])
        
        elif cmd == 'SREM':
            if len(args) < 2:
                return RedisError("wrong number of arguments for 'srem' command")
            return self.store.srem(args[0], *args[1:])
        
        elif cmd == 'SMEMBERS':
            if len(args) < 1:
                return RedisError("wrong number of arguments for 'smembers' command")
            return list(self.store.smembers(args[0]))
        
        elif cmd == 'SISMEMBER':
            if len(args) < 2:
                return RedisError("wrong number of arguments for 'sismember' command")
            return 1 if self.store.sismember(args[0], args[1]) else 0
        
        elif cmd == 'SCARD':
            if len(args) < 1:
                return RedisError("wrong number of arguments for 'scard' command")
            return self.store.scard(args[0])
        
        # 服务器管理
        elif cmd == 'INFO':
            section = args[0] if args else 'server'
            return self._get_info(section)
        
        elif cmd == 'DBSIZE':
            return len(self.store.data)
        
        elif cmd == 'FLUSHDB':
            self.store.flushdb()
            return 'OK'
        
        elif cmd == 'FLUSHALL':
            self.store.flushdb()
            return 'OK'
        
        elif cmd == 'SAVE':
            self._save_data()
            return 'OK'
        
        elif cmd == 'COMMAND':
            # 返回命令文档 (简化版)
            return [
                # 键值操作
                'SET', 'GET', 'DEL', 'EXISTS', 'KEYS', 'TTL', 'EXPIRE', 'EXPIREAT',
                'PEXPIRE', 'PEXPIREAT', 'PERSIST', 'PTTL', 'TYPE',
                'MGET', 'MSET', 'MSETNX', 'SETNX', 'SETEX', 'GETSET',
                # 计数器
                'INCR', 'DECR', 'INCRBY', 'DECRBY', 'INCRBYFLOAT',
                # List 操作
                'LPUSH', 'RPUSH', 'LPOP', 'RPOP', 'LLEN', 'LRANGE', 'LTRIM',
                'LINDEX', 'LSET', 'RPOPLPUSH', 'BLPOP', 'BRPOP',
                # Hash 操作
                'HSET', 'HMSET', 'HMGET', 'HGET', 'HGETALL', 'HDEL', 'HEXISTS',
                'HKEYS', 'HVALS', 'HLEN', 'HINCRBY', 'HINCRBYFLOAT', 'HSETNX',
                # Set 操作
                'SADD', 'SREM', 'SMEMBERS', 'SISMEMBER', 'SCARD',
                # 服务器管理
                'PING', 'ECHO', 'AUTH', 'INFO', 'DBSIZE', 'FLUSHDB', 'FLUSHALL',
                'SAVE', 'QUIT', 'SHUTDOWN', 'COMMAND', 'CONFIG'
            ]
        
        elif cmd == 'CONFIG':
            if len(args) < 2:
                return RedisError("wrong number of arguments for 'config' command")
            if args[0].upper() == 'GET':
                return []  # 简化实现
            return 'OK'
        
        elif cmd == 'QUIT':
            return 'OK'
        
        elif cmd == 'SHUTDOWN':
            self.running = False
            self._save_data()
            return 'OK'
        
        else:
            return RedisError(f"unknown command '{cmd}'")
    
    def _get_info(self, section: str) -> str:
        """获取服务器信息"""
        info_sections = {
            'server': f"""# Server
redis_version:7.0.0-py
redis_mode:standalone
os:{sys.platform}
arch_bits:64
tcp_port:{self.port}
uptime_in_seconds:{int(time.time() - self.start_time)}
uptime_in_days:{int((time.time() - self.start_time) / 86400)}
""",
            'memory': f"""# Memory
used_memory:{self.store.current_memory}
used_memory_human:{self.store.current_memory // 1024}K
maxmemory:{self.store.max_memory}
maxmemory_human:{self.store.max_memory // 1024 // 1024}M
""",
            'stats': f"""# Stats
total_connections_received:{self.stats['total_connections']}
total_commands_processed:{self.stats['total_commands']}
total_net_input_bytes:{self.stats['total_bytes_read']}
total_net_output_bytes:{self.stats['total_bytes_written']}
""",
            'keyspace': f"""# Keyspace
db0:keys={len(self.store.data)},expires={len(self.store.expires)}
"""
        }
        
        if section == 'default':
            return ''.join(info_sections.values())
        return info_sections.get(section, info_sections['server'])
    
    def handle_client(self, client_socket: socket.socket, address: tuple):
        """处理客户端连接"""
        self.stats['total_connections'] += 1
        print(f"[INFO] 客户端连接: {address}")
        
        buffer = b''
        authenticated = self.password is None
        
        try:
            while self.running:
                try:
                    data = client_socket.recv(4096)
                    if not data:
                        break
                    
                    self.stats['total_bytes_read'] += len(data)
                    buffer += data
                    
                    # 尝试解析完整的命令
                    while buffer:
                        command, consumed = RESPParser.parse(buffer)
                        if consumed == 0:
                            break
                        
                        buffer = buffer[consumed:]
                        
                        # 处理命令
                        if isinstance(command, list):
                            result = self.handle_command(command, authenticated)
                        elif isinstance(command, str):
                            # 内联命令
                            parts = command.split()
                            result = self.handle_command(parts, authenticated)
                        else:
                            result = RedisError("invalid command format")
                        
                        # 如果 AUTH 命令成功，更新认证状态
                        if isinstance(command, list) and command and command[0].upper() == 'AUTH':
                            if result == 'OK':
                                authenticated = True
                                print(f"[INFO] 客户端 {address} 认证成功")
                        
                        # 发送响应
                        response = RESPParser.encode(result)
                        client_socket.sendall(response)
                        self.stats['total_bytes_written'] += len(response)
                
                except socket.timeout:
                    continue
                except ConnectionResetError:
                    break
        
        except Exception as e:
            print(f"[ERROR] 处理客户端 {address} 时出错: {e}")
        
        finally:
            client_socket.close()
            print(f"[INFO] 客户端断开: {address}")
    
    def start(self):
        """启动服务"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # 检查端口是否可用
        try:
            self.server_socket.bind((self.host, self.port))
        except OSError as e:
            if e.errno == 98:  # Address already in use
                print(f"[WARN] 端口 {self.port} 已被占用，内置 Redis 服务启动失败")
                print(f"[INFO] 可能原因: 1) 另一个 Redis 实例正在运行  2) 之前的服务未正确关闭")
                print(f"[INFO] 解决方案: 设置 REDIS_SERVER_ENABLED=False 禁用内置 Redis，或更换端口 REDIS_SERVER_PORT")
                self.server_socket.close()
                return
            raise
        
        self.server_socket.listen(100)
        self.server_socket.settimeout(1)
        self.running = True
        
        print(f"[INFO] Redis 服务启动于 {self.host}:{self.port}")
        print(f"[INFO] 最大内存: {self.store.max_memory // 1024 // 1024}MB")
        print(f"[INFO] 密码保护: {'是' if self.password else '否'}")
        print(f"[INFO] 持久化文件: {self.rdb_file}")
        print("-" * 50)
        
        # 启动定期清理过期 key 的线程
        cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        cleanup_thread.start()
        
        # 启动定期保存的线程
        save_thread = threading.Thread(target=self._save_worker, daemon=True)
        save_thread.start()
        
        try:
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    client_socket.settimeout(300)  # 5分钟超时
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address),
                        daemon=True
                    )
                    client_thread.start()
                except socket.timeout:
                    continue
        
        except KeyboardInterrupt:
            print("\n[INFO] 收到中断信号，正在关闭...")
        
        finally:
            self.stop()
    
    def stop(self):
        """停止服务"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        self._save_data()
        print("[INFO] Redis 服务已停止")
    
    def _cleanup_worker(self):
        """定期清理过期 key"""
        while self.running:
            time.sleep(60)
            self.store.cleanup_expired()
    
    def _save_worker(self):
        """定期保存数据"""
        while self.running:
            time.sleep(300)  # 每5分钟保存一次
            if self.running:
                self._save_data()


def load_config(config_path: str) -> Dict[str, Any]:
    """从配置文件加载配置"""
    config = {}
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            print(f"[INFO] 加载配置文件: {config_path}")
        except Exception as e:
            print(f"[WARN] 加载配置文件失败: {e}")
    
    return config


def expand_env_vars(value: Any) -> Any:
    """展开环境变量"""
    if isinstance(value, str):
        # 处理 ${VAR:-default} 格式
        import re
        pattern = r'\$\{([^}]+)\}'
        
        def replace_env(match):
            expr = match.group(1)
            if ':-' in expr:
                var_name, default = expr.split(':-', 1)
                return os.environ.get(var_name, default)
            return os.environ.get(expr, '')
        
        return re.sub(pattern, replace_env, value)
    return value

def create_redis_server(
    host: str = '0.0.0.0',
    port: int = 6379,
    max_memory_mb: int = 128,
    password: Optional[str] = None,
    config_path: Optional[str] = None
) -> RedisServer:
    """
    创建 Redis 服务器实例
    
    可以直接调用此函数创建服务器，然后调用 server.start() 启动
    
    Args:
        host: 监听地址
        port: 监听端口
        max_memory_mb: 最大内存 MB
        password: 认证密码
        config_path: 配置文件路径，如果提供则会从中读取配置
    
    Returns:
        RedisServer 实例
    
    Example:
        # 直接使用参数
        server = create_redis_server(port=6380, max_memory_mb=256)
        server.start()
        
        # 从配置文件创建
        server = create_redis_server(config_path='./config.yaml')
        server.start()
    """
    # 如果提供了配置文件，从中加载配置
    if config_path:
        config = load_config(config_path)
        redis_config = config.get('redis', {})
        server_config = redis_config.get('server', {})
        
        # 配置文件中的值作为默认值，参数优先
        host = host if host != '0.0.0.0' else expand_env_vars(server_config.get('host', host))
        port = port if port != 6379 else int(expand_env_vars(server_config.get('port', port)))
        max_memory_mb = max_memory_mb if max_memory_mb != 128 else int(expand_env_vars(server_config.get('max_memory', max_memory_mb)))
        if password is None:
            password = expand_env_vars(server_config.get('password', ''))
            if password == '':
                password = None
    
    return RedisServer(
        host=host,
        port=port,
        max_memory_mb=max_memory_mb,
        password=password
    )


def run_redis_server(
    host: str = '0.0.0.0',
    port: int = 6379,
    max_memory_mb: int = 128,
    password: Optional[str] = None,
    config_path: Optional[str] = None,
    blocking: bool = False
) -> Optional[RedisServer]:
    """
    运行 Redis 服务器
    
    Args:
        host: 监听地址
        port: 监听端口
        max_memory_mb: 最大内存 MB
        password: 认证密码
        config_path: 配置文件路径
        blocking: 是否阻塞运行。如果为 False，将在后台线程运行
    
    Returns:
        如果 blocking=False，返回 RedisServer 实例；否则返回 None
    
    Example:
        # 阻塞运行（默认）
        run_redis_server(port=6379)
        
        # 后台运行
        server = run_redis_server(port=6379, blocking=False)
        # ... 做其他事情 ...
        server.stop()  # 停止服务器
    """
    server = create_redis_server(
        host=host,
        port=port,
        max_memory_mb=max_memory_mb,
        password=password,
        config_path=config_path
    )
    
    if blocking:
        # 阻塞模式：直接运行
        server.start()
        return None
    else:
        # 非阻塞模式：在后台线程运行
        server_thread = threading.Thread(target=server.start, daemon=True)
        server_thread.start()
        # 等待服务器启动
        time.sleep(0.1)
        return server


def start_redis_server():
    """命令行入口"""
    parser = argparse.ArgumentParser(description='Python 实现的轻量级 Redis 服务端')
    parser.add_argument('--host', default=None, help='监听地址')
    parser.add_argument('--port', type=int, default=None, help='监听端口')
    parser.add_argument('--max-memory', type=int, default=None, help='最大内存 MB')
    parser.add_argument('--password', default=None, help='认证密码')
    parser.add_argument('--config', default=None, help='配置文件路径')
    parser.add_argument('--daemon', action='store_true', help='以守护进程运行')
    
    args = parser.parse_args()
    
    # 确定配置文件路径
    config_path = args.config
    if config_path is None:
        # 尝试查找默认配置文件
        script_dir = os.path.dirname(os.path.abspath(__file__))
        possible_paths = [
            os.path.join(script_dir, '..', 'config.yaml'),
            os.path.join(script_dir, '..', '..', 'config.yaml'),
            './config.yaml',
        ]
        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                break
    
    # 加载配置文件
    config = {}
    if config_path:
        config = load_config(config_path)
    
    # 从配置文件获取 redis.server 配置
    redis_config = config.get('redis', {})
    server_config = redis_config.get('server', {})
    
    # 合并命令行参数和配置文件 (命令行优先)
    host = args.host if args.host is not None else expand_env_vars(server_config.get('host', '0.0.0.0'))
    port = args.port if args.port is not None else expand_env_vars(server_config.get('port', 6379))
    max_memory = args.max_memory if args.max_memory is not None else expand_env_vars(server_config.get('max_memory', 128))
    password = args.password if args.password is not None else expand_env_vars(server_config.get('password', ''))
    
    # 转换类型
    if isinstance(port, str):
        port = int(port)
    if isinstance(max_memory, str):
        max_memory = int(max_memory)
    if password == '' or password is None:
        password = None
    
    server = RedisServer(
        host=host,
        port=port,
        max_memory_mb=max_memory,
        password=password
    )
    
    # 信号处理
    def signal_handler(sig, frame):
        server.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    server.start()


if __name__ == '__main__':
    start_redis_server()
