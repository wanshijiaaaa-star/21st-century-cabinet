"""验证级联凭证是否匹配"""
import sys
import os
import hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.db import DB
from core.models.cascade_node import CascadeNode
from core.config import cfg

def main():
    session = DB.get_session()
    
    # 从配置获取凭证
    cascade_config = cfg.get("cascade", {})
    config_ak = cascade_config.get("api_key", "").strip().strip('"\'')
    config_sk = cascade_config.get("api_secret", "").strip().strip('"\'')
    
    print("=" * 60)
    print("级联凭证验证")
    print("=" * 60)
    
    print(f"\n配置文件中的 AK: {config_ak}")
    print(f"配置文件中的 SK: {config_sk}")
    
    # 计算 SK 哈希
    if config_sk:
        config_sk_hash = hashlib.sha256(config_sk.encode()).hexdigest()
        print(f"配置 SK 的哈希: {config_sk_hash}")
    else:
        print("配置 SK 为空!")
        return 1
    
    # 查询数据库
    print("\n" + "-" * 60)
    print("数据库中的子节点:")
    print("-" * 60)
    
    nodes = session.query(CascadeNode).filter(
        CascadeNode.node_type == 1
    ).all()
    
    if not nodes:
        print("❌ 数据库中没有子节点记录!")
        print("\n请运行以下命令创建子节点:")
        print("  python setup_cascade_child.py")
        return 1
    
    found_match = False
    for node in nodes:
        print(f"\n节点: {node.name}")
        print(f"  ID: {node.id}")
        print(f"  AK: {node.api_key}")
        print(f"  SK Hash: {node.api_secret_hash}")
        print(f"  Active: {node.is_active}")
        
        ak_match = node.api_key == config_ak
        sk_match = node.api_secret_hash == config_sk_hash
        
        print(f"  AK 匹配: {'✅' if ak_match else '❌'}")
        print(f"  SK 匹配: {'✅' if sk_match else '❌'}")
        
        if ak_match and sk_match:
            found_match = True
            print("  ✅ 凭证完全匹配!")
    
    if not found_match:
        print("\n" + "=" * 60)
        print("❌ 没有找到匹配的凭证!")
        print("=" * 60)
        print("\n解决方案:")
        print("1. 运行 python setup_cascade_child.py 创建新凭证")
        print("2. 将输出的 AK/SK 更新到 config.yaml")
        print("3. 重启服务")
    else:
        print("\n" + "=" * 60)
        print("✅ 凭证验证通过!")
        print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
