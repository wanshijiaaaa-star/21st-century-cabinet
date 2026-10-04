"""
快速修复损坏的 SQLite 数据库
直接运行此脚本: python fix_db_now.py
"""
import sqlite3
import os
import shutil
from datetime import datetime

DB_PATH = 'data/db.db'

def main():
    print("=" * 50)
    print("SQLite 数据库修复工具")
    print("=" * 50)
    
    if not os.path.exists(DB_PATH):
        print(f"数据库文件不存在: {DB_PATH}")
        return
    
    # 1. 检查完整性
    print("\n[1/4] 检查数据库完整性...")
    try:
        conn = sqlite3.connect(DB_PATH)
        result = conn.execute('PRAGMA integrity_check').fetchone()[0]
        conn.close()
        print(f"结果: {result}")
        if result == 'ok':
            print("数据库完整性正常，无需修复")
            return
    except Exception as e:
        print(f"检查失败: {e}")
    
    # 2. 备份
    print("\n[2/4] 备份原数据库...")
    backup_path = f'{DB_PATH}.bak_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    try:
        shutil.copy2(DB_PATH, backup_path)
        print(f"已备份到: {backup_path}")
    except Exception as e:
        print(f"备份失败: {e}")
        return
    
    # 3. 尝试使用 sqlite3 命令行工具修复
    print("\n[3/4] 尝试使用 sqlite3 命令修复...")
    dump_sql = f'{DB_PATH}.sql'
    recovered_db = f'{DB_PATH}.new'
    
    # 使用 .dump 导出
    ret = os.system(f'sqlite3 "{DB_PATH}" ".dump" > "{dump_sql}" 2>&1')
    if ret != 0:
        print("sqlite3 dump 失败，尝试 Python 方式...")
        
        # Python 方式导出
        try:
            conn_old = sqlite3.connect(DB_PATH)
            conn_new = sqlite3.connect(recovered_db)
            
            cursor_old = conn_old.cursor()
            cursor_new = conn_new.cursor()
            
            # 获取所有表
            cursor_old.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = cursor_old.fetchall()
            
            total_rows = 0
            for table_name, create_sql in tables:
                if not create_sql:
                    continue
                try:
                    cursor_new.execute(create_sql)
                    cursor_old.execute(f'SELECT * FROM "{table_name}"')
                    rows = cursor_old.fetchall()
                    if rows:
                        placeholders = ','.join(['?' for _ in rows[0]])
                        cursor_new.executemany(f'INSERT INTO "{table_name}" VALUES ({placeholders})', rows)
                        total_rows += len(rows)
                        print(f"  {table_name}: {len(rows)} 行")
                except Exception as e:
                    print(f"  {table_name}: 跳过 ({e})")
            
            # 创建索引
            cursor_old.execute("SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL")
            for (idx_sql,) in cursor_old.fetchall():
                try:
                    cursor_new.execute(idx_sql)
                except:
                    pass
            
            conn_new.commit()
            conn_old.close()
            conn_new.close()
            
            print(f"共恢复 {total_rows} 行数据")
            
        except Exception as e:
            print(f"Python 方式修复失败: {e}")
            return
    else:
        # 从 dump 恢复
        print(f"已导出 SQL: {dump_sql}")
        if os.path.exists(recovered_db):
            os.remove(recovered_db)
        os.system(f'sqlite3 "{recovered_db}" < "{dump_sql}"')
    
    # 4. 验证并替换
    print("\n[4/4] 验证新数据库...")
    if not os.path.exists(recovered_db):
        print("新数据库文件不存在，修复失败")
        return
    
    try:
        conn = sqlite3.connect(recovered_db)
        result = conn.execute('PRAGMA integrity_check').fetchone()[0]
        conn.close()
        print(f"新数据库完整性: {result}")
        
        if result == 'ok':
            # 替换原数据库
            os.remove(DB_PATH)
            shutil.move(recovered_db, DB_PATH)
            print("\n✓ 修复成功！已替换原数据库")
            print(f"  备份文件: {backup_path}")
            
            # 清理临时文件
            if os.path.exists(dump_sql):
                os.remove(dump_sql)
        else:
            print("新数据库仍有问题，未替换原文件")
            print(f"  新数据库保存在: {recovered_db}")
            
    except Exception as e:
        print(f"验证失败: {e}")

if __name__ == '__main__':
    main()
    input("\n按回车键退出...")
