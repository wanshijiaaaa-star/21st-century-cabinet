"""检查级联节点凭证"""
import hashlib
import sys
sys.path.insert(0, '.')

from core.db import DB
from core.models.cascade_node import CascadeNode

session = DB.get_session()
nodes = session.query(CascadeNode).all()

print("=== 数据库中的级联节点 ===")
for node in nodes:
    print(f"ID: {node.id}")
    print(f"Name: {node.name}")
    print(f"Type: {node.node_type} (0=parent, 1=child)")
    print(f"API Key: {node.api_key}")
    print(f"API Secret Hash: {node.api_secret_hash}")
    print(f"Is Active: {node.is_active}")
    print("---")

# 计算配置中的 SK 哈希
config_sk = "CSkWFiEgSrjGKS1FESjLhmug6kCV-5pAPy"
config_hash = hashlib.sha256(config_sk.encode()).hexdigest()
print(f"\n配置中的 SK: {config_sk}")
print(f"配置中的 SK 哈希: {config_hash}")

# 检查是否有匹配的节点
config_ak = "CNS8NFByT2Kpip-GEkU5eDhPYOuxUCLi1r"
matching = session.query(CascadeNode).filter(
    CascadeNode.api_key == config_ak
).first()

if matching:
    print(f"\n找到匹配 AK 的节点: {matching.name}")
    print(f"数据库中的哈希: {matching.api_secret_hash}")
    print(f"计算的哈希: {config_hash}")
    print(f"哈希匹配: {matching.api_secret_hash == config_hash}")
else:
    print(f"\n未找到 AK 为 {config_ak} 的节点!")
    print("需要在父节点上创建子节点并生成凭证")
