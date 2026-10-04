"""级联任务分配模型 - 持久化任务分配记录，支持任务互斥"""

from .base import Base, Column, String, Integer, DateTime, Text, Boolean
from datetime import datetime


class CascadeTaskAllocation(Base):
    """
    级联任务分配记录
    
    用于：
    1. 持久化任务分配关系（任务->节点）
    2. 实现任务互斥机制（一个任务只能被一个节点获取）
    3. 追踪任务执行状态
    """
    from_attributes = True
    __tablename__ = 'cascade_task_allocations'
    
    id = Column(String(255), primary_key=True)  # 分配记录ID
    
    # 任务信息
    task_id = Column(String(255), nullable=False, index=True)  # 关联的 MessageTask ID
    task_name = Column(String(255))  # 任务名称（冗余，便于查询）
    cron_exp = Column(String(100))  # cron表达式（冗余）
    
    # 节点信息
    node_id = Column(String(255), nullable=True, index=True)  # 分配给的子节点ID，NULL表示待认领
    
    # 公众号列表
    feed_ids = Column(Text, nullable=False)  # JSON数组，分配的公众号ID列表
    
    # 状态: pending=待执行, claimed=已认领, executing=执行中, completed=已完成, failed=失败, timeout=超时
    status = Column(String(20), default='pending', index=True)
    
    # 执行信息
    result_summary = Column(Text)  # 执行结果摘要（JSON格式）
    error_message = Column(Text)  # 错误信息
    
    # 时间戳
    dispatched_at = Column(DateTime, default=datetime.utcnow)  # 任务下发时间
    claimed_at = Column(DateTime)  # 节点认领时间
    started_at = Column(DateTime)  # 开始执行时间
    completed_at = Column(DateTime)  # 完成时间
    
    # 调度相关
    schedule_run_id = Column(String(255), index=True)  # 调度批次ID（同一批次下发多个任务）
    
    # 文章数据上行统计
    article_count = Column(Integer, default=0)  # 抓取文章数
    new_article_count = Column(Integer, default=0)  # 新文章数
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """转换为字典"""
        import json
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "node_id": self.node_id,
            "feed_ids": json.loads(self.feed_ids) if self.feed_ids else [],
            "status": self.status,
            "result_summary": json.loads(self.result_summary) if self.result_summary else None,
            "error_message": self.error_message,
            "dispatched_at": self.dispatched_at.isoformat() if self.dispatched_at else None,
            "claimed_at": self.claimed_at.isoformat() if self.claimed_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "schedule_run_id": self.schedule_run_id,
            "article_count": self.article_count,
            "new_article_count": self.new_article_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
