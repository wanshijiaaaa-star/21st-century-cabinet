"""
修复用户ID类型问题的脚本
将所有整数类型的用户ID转换为UUID字符串类型
"""
from core.db import DB
from core.models.user import User
import uuid

def fix_user_ids():
    """修复用户ID类型"""
    session = DB.get_session()
    try:
        # 查询所有用户
        users = session.query(User).all()
        
        fixed_count = 0
        for user in users:
            # 检查ID是否为整数类型
            if isinstance(user.id, int) or (isinstance(user.id, str) and user.id.isdigit()):
                print(f"发现整数ID用户: {user.username} (ID: {user.id})")
                
                # 生成新的UUID
                new_id = str(uuid.uuid4())
                
                # 更新用户ID
                user.id = new_id
                fixed_count += 1
                print(f"  -> 已更新为: {new_id}")
        
        if fixed_count > 0:
            session.commit()
            print(f"\n成功修复 {fixed_count} 个用户的ID类型")
        else:
            print("\n所有用户ID类型正常，无需修复")
            
    except Exception as e:
        session.rollback()
        print(f"修复失败: {str(e)}")
    finally:
        session.close()

if __name__ == '__main__':
    print("开始修复用户ID类型...")
    fix_user_ids()
