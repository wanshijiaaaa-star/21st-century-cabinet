"""WebSocket 连接管理器"""
import asyncio
import json
from typing import Set
from fastapi import WebSocket
from core.log import logger


class WebSocketManager:
    """WebSocket 连接管理器，用于广播队列状态更新"""
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connections: Set[WebSocket] = set()
            cls._instance._loop = None
        return cls._instance
    
    async def connect(self, websocket: WebSocket):
        """接受新的 WebSocket 连接"""
        await websocket.accept()
        self._connections.add(websocket)
        logger.info(f"WebSocket 连接已建立，当前连接数: {len(self._connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """移除 WebSocket 连接"""
        self._connections.discard(websocket)
        logger.info(f"WebSocket 连接已断开，当前连接数: {len(self._connections)}")
    
    async def broadcast(self, message: dict):
        """向所有连接广播消息"""
        if not self._connections:
            return
        
        message_json = json.dumps(message, ensure_ascii=False)
        disconnected = set()
        
        for connection in self._connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.warning(f"WebSocket 发送消息失败: {e}")
                disconnected.add(connection)
        
        # 清理断开的连接
        for conn in disconnected:
            self._connections.discard(conn)
    
    def broadcast_sync(self, message: dict):
        """同步方法广播消息（从非异步上下文调用）"""
        if not self._connections:
            return
        
        try:
            # 尝试获取运行中的事件循环
            try:
                loop = asyncio.get_running_loop()
                # 如果有运行中的循环，创建任务
                asyncio.create_task(self.broadcast(message))
            except RuntimeError:
                # 没有运行中的循环，尝试获取或创建新循环
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    loop.call_soon_threadsafe(
                        lambda: asyncio.create_task(self.broadcast(message))
                    )
                except Exception as e:
                    logger.warning(f"WebSocket 广播失败（无事件循环）: {e}")
        except Exception as e:
            logger.warning(f"WebSocket 广播失败: {e}")
    
    @property
    def connection_count(self) -> int:
        """当前连接数"""
        return len(self._connections)


# 全局单例
ws_manager = WebSocketManager()
