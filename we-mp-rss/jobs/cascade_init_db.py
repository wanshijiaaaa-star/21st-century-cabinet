"""初始化级联系统数据库表"""

from core.db import DB
from core.print import print_info, print_success, print_error

def init_cascade_tables():
    """初始化级联系统表"""
    try:
        # 导入级联模型（这会注册到 Base.metadata 中）
        from core.models.cascade_node import CascadeNode, CascadeSyncLog

        # 创建表
        from core.models.base import Base
        Base.metadata.create_all(DB.get_engine())

        print_success("级联系统表创建成功")
        print_info("已创建表：cascade_nodes, cascade_sync_logs")
        return True
    except Exception as e:
        print_error(f"初始化级联表失败: {str(e)}")
        return False

if __name__ == '__main__':
    init_cascade_tables()
