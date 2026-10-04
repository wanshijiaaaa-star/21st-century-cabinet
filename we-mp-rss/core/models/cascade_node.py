from .base import Base, Column, String, Integer, DateTime, Text, Boolean
from datetime import datetime

class CascadeNode(Base):
    """级联节点模型 - 支持父子节点架构"""
    from_attributes = True
    __tablename__ = 'cascade_nodes'
    
    id = Column(String(255), primary_key=True)  # 节点ID
    node_type = Column(Integer, nullable=False, default=0)  # 节点类型: 0=父节点, 1=子节点
    name = Column(String(255), nullable=False)  # 节点名称
    description = Column(Text)  # 节点描述
    api_url = Column(String(500))  # API地址 (子节点配置父节点地址时使用)
    callback_url = Column(String(500))  # 回调地址 (网关通知子节点时使用)
    api_key = Column(String(100))  # 认证AK (子节点连接父节点使用)
    api_secret_hash = Column(String(64))  # 认证SK哈希值
    parent_id = Column(String(255))  # 父节点ID (仅子节点使用)
    status = Column(Integer, default=0)  # 状态: 0=离线, 1=在线, 2=已停用
    sync_config = Column(Text, default='{}')  # 同步配置(JSON格式)
    last_sync_at = Column(DateTime)  # 最后同步时间
    last_heartbeat_at = Column(DateTime)  # 最后心跳时间
    is_active = Column(Boolean, default=True)  # 是否启用
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CascadeSyncLog(Base):
    """级联同步日志 - 记录父子节点间的同步操作"""
    from_attributes = True
    __tablename__ = 'cascade_sync_logs'

    id = Column(String(255), primary_key=True)
    node_id = Column(String(255), nullable=False)  # 节点ID
    operation = Column(String(50), nullable=False)  # 操作类型: sync_feeds, sync_tasks, report_result等
    direction = Column(String(20), nullable=False)  # 方向: pull(从父拉取), push(向父推送)
    status = Column(Integer, default=0)  # 状态: 0=进行中, 1=成功, 2=失败
    data_count = Column(Integer, default=0)  # 数据条数
    error_message = Column(Text)  # 错误信息
    extra_data = Column(Text, default='{}')  # 额外数据(JSON格式)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
