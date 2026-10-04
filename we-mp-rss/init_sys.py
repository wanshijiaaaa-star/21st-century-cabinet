from core.models.user import User
from core.models.article import Article
from core.models.config_management import ConfigManagement
from core.models.feed import Feed
from core.models.message_task import MessageTask
from core.models.cascade_node import CascadeNode, CascadeSyncLog
from core.models.cascade_task_allocation import CascadeTaskAllocation
from core.models.filter_rule import FilterRule
from core.db import Db,DB
from core.config import cfg
from core.auth import pwd_context
import time
import os
from core.print import print_info, print_error
def init_user(_db: Db):
    try:
      username = os.getenv("WERSS_ADMIN_USER", cfg.get("admin.username", "admin"))
      password = os.getenv("WERSS_ADMIN_PASSWORD", "")
      session=_db.get_session()
      
      # 检查用户是否已存在
      existing_user = session.query(User).filter(User.username == username).first()
      
      if existing_user:
          # 用户已存在，更新为管理员权限
          existing_user.role = 'admin'
          existing_user.is_active = True
          session.commit()
          print_info(f"用户已存在，已更新为管理员权限：{username}")
      else:
          if not password:
              raise ValueError("首次启动必须通过 WERSS_ADMIN_PASSWORD 设置管理员密码")
          # 用户不存在，创建新用户
          import uuid
          session.add(User(
              id=0,
              username=username,
              password_hash=pwd_context.hash(password),
              role='admin',
              is_active=True,
          ))
          session.commit()
          print_info(f"初始化用户成功,请使用以下凭据登录：{username}")
    except Exception as e:
        print_error(f"初始化管理员失败: {str(e)}")
        raise
def sync_models():
     # 同步模型到表结构
         from data_sync import DatabaseSynchronizer
         DB.create_tables()
         time.sleep(3)
         synchronizer = DatabaseSynchronizer(db_url=cfg.get("db",""))
         synchronizer.sync()
         print_info("模型同步完成")

     

 
def init():
    sync_models()
    init_user(DB)

if __name__ == '__main__':
    init()
