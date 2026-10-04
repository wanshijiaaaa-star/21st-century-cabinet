#!/usr/bin/env python3
"""
数据库迁移脚本：为 message_tasks 表添加 headers 和 cookies 字段
执行方式：python migrations/add_headers_cookies_fields.py
"""
from core.db import DB
from core.config import cfg
from sqlalchemy import text
from core.print import print_info, print_error, print_success

def migrate():
    """执行数据库迁移"""
    print_info("开始迁移：为 message_tasks 表添加 headers 和 cookies 字段")

    engine = DB.get_engine()
    session = DB.get_session()

    try:
        # 检查表是否存在
        inspector = engine.dialect.get Inspector(engine)
        if 'message_tasks' not in inspector.get_table_names():
            print_error("message_tasks 表不存在，跳过迁移")
            return

        # 获取现有列
        columns = [col['name'] for col in inspector.get_columns('message_tasks')]

        # 检查并添加 headers 字段
        if 'headers' not in columns:
            print_info("添加 headers 字段...")
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE message_tasks ADD COLUMN headers TEXT"))
                conn.commit()
            print_success("headers 字段添加成功")
        else:
            print_info("headers 字段已存在，跳过")

        # 检查并添加 cookies 字段
        if 'cookies' not in columns:
            print_info("添加 cookies 字段...")
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE message_tasks ADD COLUMN cookies TEXT"))
                conn.commit()
            print_success("cookies 字段添加成功")
        else:
            print_info("cookies 字段已存在，跳过")

        print_success("数据库迁移完成！")

    except Exception as e:
        print_error(f"数据库迁移失败: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    migrate()
