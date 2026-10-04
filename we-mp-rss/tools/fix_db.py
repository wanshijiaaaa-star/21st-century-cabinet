"""
SQLite 数据库修复工具
用于修复损坏的数据库文件
"""
import sqlite3
import os
import shutil
import re
from datetime import datetime


def validate_table_name(table_name: str) -> bool:
    """
    安全加固：验证表名是否合法

    Args:
        table_name: 表名

    Returns:
        bool: 是否合法
    """
    # 表名必须以字母或下划线开头，只能包含字母、数字、下划线
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*

def check_integrity(db_path: str) -> tuple:
    """检查数据库完整性"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        result = cursor.execute('PRAGMA integrity_check').fetchall()
        conn.close()
        return True, result
    except Exception as e:
        return False, str(e)

def repair_database(db_path: str) -> bool:
    """尝试修复损坏的数据库"""
    backup_path = f'{db_path}.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    recovered_path = f'{db_path}.recovered'
    
    # 1. 备份原数据库
    if os.path.exists(db_path):
        shutil.copy2(db_path, backup_path)
        print(f'已备份原数据库到: {backup_path}')
    
    # 2. 尝试使用 .dump 恢复
    dump_file = f'{db_path}.dump.sql'
    
    try:
        # 导出数据
        conn_old = sqlite3.connect(db_path)
        
        # 创建新数据库
        if os.path.exists(recovered_path):
            os.remove(recovered_path)
        
        conn_new = sqlite3.connect(recovered_path)
        
        # 获取所有表的创建语句
        cursor_old = conn_old.cursor()
        cursor_old.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = cursor_old.fetchall()
        
        cursor_new = conn_new.cursor()

        for table_name, create_sql in tables:
            if not create_sql:
                continue

            # 安全加固：验证表名
            if not validate_table_name(table_name):
                print(f'跳过非法表名: {table_name}')
                continue

            try:
                # 创建表
                cursor_new.execute(create_sql)
                print(f'创建表: {table_name}')

                # 复制数据（安全加固：验证表名后使用）
                try:
                    # 表名已验证，可以安全使用
                    cursor_old.execute(f'SELECT * FROM "{table_name}"')
                    rows = cursor_old.fetchall()
                    if rows:
                        placeholders = ','.join(['?' for _ in rows[0]])
                        cursor_new.executemany(f'INSERT INTO "{table_name}" VALUES ({placeholders})', rows)
                        print(f'  复制 {len(rows)} 行数据')
                except Exception as e:
                    print(f'  复制数据失败: {e}')

            except Exception as e:
                print(f'创建表 {table_name} 失败: {e}')
        
        # 复制索引
        cursor_old.execute("SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL")
        indexes = cursor_old.fetchall()
        for (index_sql,) in indexes:
            try:
                cursor_new.execute(index_sql)
            except Exception as e:
                print(f'创建索引失败: {e}')
        
        conn_new.commit()
        conn_old.close()
        conn_new.close()
        
        # 验证新数据库
        ok, result = check_integrity(recovered_path)
        if ok and result[0][0] == 'ok':
            # 替换原数据库
            os.remove(db_path)
            shutil.move(recovered_path, db_path)
            print(f'\n修复成功！已替换原数据库')
            return True
        else:
            print(f'\n修复后数据库仍有问题: {result}')
            return False
            
    except Exception as e:
        print(f'修复过程出错: {e}')
        return False

if __name__ == '__main__':
    import sys
    
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'data/db.db'
    
    print(f'检查数据库: {db_path}')
    ok, result = check_integrity(db_path)
    
    if ok:
        print(f'完整性检查结果: {result}')
        if result[0][0] == 'ok':
            print('数据库完整性正常')
        else:
            print('数据库损坏，尝试修复...')
            repair_database(db_path)
    else:
        print(f'无法打开数据库: {result}')
        print('尝试修复...')
        repair_database(db_path)
, table_name):
        return False
    # 长度限制
    if len(table_name) > 128:
        return False
    return True

def check_integrity(db_path: str) -> tuple:
    """检查数据库完整性"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        result = cursor.execute('PRAGMA integrity_check').fetchall()
        conn.close()
        return True, result
    except Exception as e:
        return False, str(e)

def repair_database(db_path: str) -> bool:
    """尝试修复损坏的数据库"""
    backup_path = f'{db_path}.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    recovered_path = f'{db_path}.recovered'
    
    # 1. 备份原数据库
    if os.path.exists(db_path):
        shutil.copy2(db_path, backup_path)
        print(f'已备份原数据库到: {backup_path}')
    
    # 2. 尝试使用 .dump 恢复
    dump_file = f'{db_path}.dump.sql'
    
    try:
        # 导出数据
        conn_old = sqlite3.connect(db_path)
        
        # 创建新数据库
        if os.path.exists(recovered_path):
            os.remove(recovered_path)
        
        conn_new = sqlite3.connect(recovered_path)
        
        # 获取所有表的创建语句
        cursor_old = conn_old.cursor()
        cursor_old.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = cursor_old.fetchall()
        
        cursor_new = conn_new.cursor()

        for table_name, create_sql in tables:
            if not create_sql:
                continue

            # 安全加固：验证表名
            if not validate_table_name(table_name):
                print(f'跳过非法表名: {table_name}')
                continue

            try:
                # 创建表
                cursor_new.execute(create_sql)
                print(f'创建表: {table_name}')

                # 复制数据（安全加固：验证表名后使用）
                try:
                    # 表名已验证，可以安全使用
                    cursor_old.execute(f'SELECT * FROM "{table_name}"')
                    rows = cursor_old.fetchall()
                    if rows:
                        placeholders = ','.join(['?' for _ in rows[0]])
                        cursor_new.executemany(f'INSERT INTO "{table_name}" VALUES ({placeholders})', rows)
                        print(f'  复制 {len(rows)} 行数据')
                except Exception as e:
                    print(f'  复制数据失败: {e}')

            except Exception as e:
                print(f'创建表 {table_name} 失败: {e}')
        
        # 复制索引
        cursor_old.execute("SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL")
        indexes = cursor_old.fetchall()
        for (index_sql,) in indexes:
            try:
                cursor_new.execute(index_sql)
            except Exception as e:
                print(f'创建索引失败: {e}')
        
        conn_new.commit()
        conn_old.close()
        conn_new.close()
        
        # 验证新数据库
        ok, result = check_integrity(recovered_path)
        if ok and result[0][0] == 'ok':
            # 替换原数据库
            os.remove(db_path)
            shutil.move(recovered_path, db_path)
            print(f'\n修复成功！已替换原数据库')
            return True
        else:
            print(f'\n修复后数据库仍有问题: {result}')
            return False
            
    except Exception as e:
        print(f'修复过程出错: {e}')
        return False

if __name__ == '__main__':
    import sys
    
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'data/db.db'
    
    print(f'检查数据库: {db_path}')
    ok, result = check_integrity(db_path)
    
    if ok:
        print(f'完整性检查结果: {result}')
        if result[0][0] == 'ok':
            print('数据库完整性正常')
        else:
            print('数据库损坏，尝试修复...')
            repair_database(db_path)
    else:
        print(f'无法打开数据库: {result}')
        print('尝试修复...')
        repair_database(db_path)
