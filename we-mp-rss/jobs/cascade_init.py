"""级联系统初始化脚本 - 用于初始化父节点或子节点"""

import sys
import os
import argparse
from core.db import DB
from core.models.cascade_node import CascadeNode
from core.models.base import Base
from core.print import print_info, print_success, print_error, print_warning
from core.config import cfg


def init_cascade_tables():
    """初始化级联相关数据表"""
    try:
        print_info("正在创建级联相关数据表...")
        
        # 初始化数据库连接
        DB.create_tables()
        
        print_success("级联数据表初始化完成")
        return True
    except Exception as e:
        print_error(f"初始化数据表失败: {str(e)}")
        return False


def create_parent_node(name="主节点"):
    """创建父节点记录"""
    try:
        session = DB.get_session()
        
        # 检查是否已存在父节点
        existing = session.query(CascadeNode).filter(
            CascadeNode.node_type == 0
        ).first()
        
        if existing:
            print_warning(f"父节点已存在: {existing.name} (ID: {existing.id})")
            return existing
        
        import uuid
        from datetime import datetime
        node = CascadeNode(
            id=str(uuid.uuid4()),
            node_type=0,
            name=name,
            description="主节点",
            status=1,  # 在线
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        session.add(node)
        session.commit()
        session.refresh(node)
        
        print_success(f"父节点创建成功: {name} (ID: {node.id})")
        return node
        
    except Exception as e:
        session.rollback()
        print_error(f"创建父节点失败: {str(e)}")
        return None


def create_child_node(name, description="", api_url=""):
    """创建子节点记录"""
    try:
        session = DB.get_session()
        
        import uuid
        from datetime import datetime
        node = CascadeNode(
            id=str(uuid.uuid4()),
            node_type=1,
            name=name,
            description=description,
            api_url=api_url,
            status=0,  # 离线
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        session.add(node)
        session.commit()
        session.refresh(node)
        
        print_success(f"子节点创建成功: {name} (ID: {node.id})")
        return node
        
    except Exception as e:
        session.rollback()
        print_error(f"创建子节点失败: {str(e)}")
        return None


def list_nodes():
    """列出所有节点"""
    try:
        session = DB.get_session()
        
        parents = session.query(CascadeNode).filter(
            CascadeNode.node_type == 0
        ).all()
        
        children = session.query(CascadeNode).filter(
            CascadeNode.node_type == 1
        ).all()
        
        print_info("\n=== 父节点 ===")
        if parents:
            for node in parents:
                print(f"ID: {node.id}")
                print(f"名称: {node.name}")
                print(f"状态: {'在线' if node.status == 1 else '离线'}")
                print(f"创建时间: {node.created_at}")
                print(f"---")
        else:
            print("无父节点")
        
        print_info("\n=== 子节点 ===")
        if children:
            for node in children:
                print(f"ID: {node.id}")
                print(f"名称: {node.name}")
                print(f"API地址: {node.api_url}")
                print(f"API Key: {node.api_key}")
                print(f"状态: {'在线' if node.status == 1 else '离线'}")
                print(f"最后心跳: {node.last_heartbeat_at}")
                print(f"---")
        else:
            print("无子节点")
            
    except Exception as e:
        print_error(f"列出节点失败: {str(e)}")


def check_config():
    """检查配置"""
    print_info("\n=== 检查级联配置 ===")
    
    cascade_config = cfg.get("cascade", {})
    
    enabled = cascade_config.get("enabled", False)
    node_type = cascade_config.get("node_type", "parent")
    parent_url = cascade_config.get("parent_api_url", "")
    api_key = cascade_config.get("api_key", "")
    
    print(f"级联模式: {'启用' if enabled else '禁用'}")
    print(f"节点类型: {node_type}")
    
    if node_type == "child":
        print(f"父节点地址: {parent_url}")
        print(f"API Key: {api_key[:10]}..." if api_key else "API Key: 未配置")
        print(f"同步间隔: {cascade_config.get('sync_interval', 300)}秒")
        print(f"心跳间隔: {cascade_config.get('heartbeat_interval', 60)}秒")
    
    # 检查配置完整性
    if enabled and node_type == "child":
        if not all([parent_url, api_key]):
            print_warning("\n警告: 子节点配置不完整!")
            print("请配置以下参数:")
            print("  - CASCADE_PARENT_URL")
            print("  - CASCADE_API_KEY")
            print("  - CASCADE_API_SECRET")
            return False
    
    print_success("\n配置检查完成")
    return True


def main():
    parser = argparse.ArgumentParser(description="WeRSS 级联系统初始化工具")
    parser.add_argument("--init", action="store_true", help="初始化数据库表")
    parser.add_argument("--parent", metavar="NAME", help="创建父节点")
    parser.add_argument("--child", metavar="NAME", help="创建子节点")
    parser.add_argument("--desc", metavar="DESC", help="节点描述")
    parser.add_argument("--api-url", metavar="URL", help="子节点API地址")
    parser.add_argument("--list", action="store_true", help="列出所有节点")
    parser.add_argument("--check", action="store_true", help="检查配置")
    
    args = parser.parse_args()
    
    if not any([args.init, args.parent, args.child, args.list, args.check]):
        parser.print_help()
        return
    
    # 初始化数据库
    if args.init:
        if not init_cascade_tables():
            sys.exit(1)
    
    # 创建父节点
    if args.parent:
        node = create_parent_node(args.parent)
        if not node:
            sys.exit(1)
    
    # 创建子节点
    if args.child:
        node = create_child_node(
            args.child,
            description=args.desc or "",
            api_url=args.api_url or ""
        )
        if not node:
            sys.exit(1)
        
        # 自动生成凭证
        if node:
            from core.cascade import cascade_manager
            credentials = cascade_manager.generate_node_credentials(node.id)
            print("\n" + "="*50)
            print("子节点凭证 (请妥善保存，仅显示一次)")
            print("="*50)
            print(f"节点ID: {credentials['node_id']}")
            print(f"API Key: {credentials['api_key']}")
            print(f"API Secret: {credentials['api_secret']}")
            print("="*50)
            print("\n请将以下配置添加到子节点的 config.yaml:")
            print(f"""
cascade:
  enabled: true
  node_type: child
  parent_api_url: {args.api_url or 'http://parent-server:8001'}
  api_key: {credentials['api_key']}
  api_secret: {credentials['api_secret']}
""")
    
    # 列出节点
    if args.list:
        list_nodes()
    
    # 检查配置
    if args.check:
        if not check_config():
            sys.exit(1)


if __name__ == "__main__":
    main()
