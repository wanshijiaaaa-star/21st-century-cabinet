from .base import Base, Column, String, Integer, DateTime, Text, JSON
from datetime import datetime


class FilterRule(Base):
    """HTML过滤规则模型 - 为指定公众号配置HTML过滤规则"""
    __tablename__ = 'filter_rules'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    mp_id = Column(String(255), nullable=False, index=True, comment='公众号ID')
    rule_name = Column(String(255), nullable=False, comment='规则名称')
    
    # 过滤规则配置
    remove_ids = Column(JSON, nullable=True, comment='要移除的ID列表')
    remove_classes = Column(JSON, nullable=True, comment='要移除的class列表')
    remove_selectors = Column(JSON, nullable=True, comment='CSS选择器列表')
    remove_attributes = Column(JSON, nullable=True, comment='属性过滤列表 [{"name": "attr_name", "value": "attr_value", "eq": true}]')
    remove_regex = Column(JSON, nullable=True, comment='正则表达式列表')
    remove_normal_tag = Column(Integer, default=0, comment='是否移除常见HTML元素(0-否, 1-是)')
    
    status = Column(Integer, default=1, comment='状态(1-启用, 2-禁用)')
    priority = Column(Integer, default=0, comment='优先级，数字越大优先级越高')
    
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    from_attributes = True
