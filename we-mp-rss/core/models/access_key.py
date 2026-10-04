from .base import Base, Column, String, DateTime, Boolean, Text, Integer
from datetime import datetime

class AccessKey(Base):
    """API Access Key 模型"""
    __tablename__ = 'access_keys'
    
    id = Column(String(255), primary_key=True)
    user_id = Column(String(255), nullable=False)  # 关联用户ID
    key = Column(String(64), unique=True, nullable=False, index=True)  # AK值
    secret = Column(String(64), nullable=False)  # SK值（密钥）
    name = Column(String(255), nullable=False)  # AK名称
    description = Column(Text, default='')  # 描述
    permissions = Column(Text, default='')  # 权限列表 (JSON格式)
    is_active = Column(Boolean, default=True)  # 是否激活
    last_used_at = Column(DateTime, nullable=True)  # 最后使用时间
    created_at = Column(DateTime, default=datetime.utcnow)  # 创建时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新时间
    expires_at = Column(DateTime, nullable=True)  # 过期时间
    
    def is_expired(self) -> bool:
        """检查是否已过期"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """检查AK是否有效"""
        return self.is_active and not self.is_expired()
