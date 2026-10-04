"""级联任务分发器使用示例"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.db import DB
from core.config import cfg
from jobs.cascade_task_dispatcher import (
    CascadeTaskDispatcher,
    cascade_task_dispatcher,
    start_child_task_worker,
    execute_parent_task
)
from core.models.message_task import MessageTask
from core.models.feed import Feed


def init_system():
    """初始化系统"""
    print("初始化系统...")
    
    # 初始化数据库
    DB.create_tables()
    
    print("系统初始化完成\n")


def example_parent_dispatch():
    """父节点任务分发示例"""
    print("="*60)
    print("父节点任务分发示例")
    print("="*60)
    
    # 初始化
    init_system()
    
    # 创建分发器
    dispatcher = CascadeTaskDispatcher()
    
    # 刷新节点状态
    print("\n1. 刷新子节点状态...")
    online_count = dispatcher.refresh_node_statuses()
    print(f"   在线节点数量: {online_count}")
    
    if online_count == 0:
        print("   警告: 没有在线子节点，请先配置并启动子节点")
        return
    
    # 显示节点状态
    print("\n2. 节点状态:")
    for node_id, status in dispatcher.node_statuses.items():
        print(f"   - {status.node_name}")
        print(f"     状态: {'在线' if status.is_online else '离线'}")
        print(f"     可用容量: {status.available_capacity}/{status.max_capacity}")
        print(f"     当前任务: {status.current_tasks}")
    
    # 分发任务
    print("\n3. 分发任务...")
    session = DB.get_session()
    
    # 获取第一个启用的任务
    task = session.query(MessageTask).filter(MessageTask.status == 0).first()
    
    if task:
        print(f"   任务名称: {task.name}")
        allocations = dispatcher.dispatch_task_to_children(task)
        
        print(f"\n4. 分配结果:")
        for node_id, feeds in allocations.items():
            node_status = dispatcher.node_statuses[node_id]
            print(f"   - {node_status.node_name}: {len(feeds)} 个公众号")
            for feed in feeds:
                print(f"     * {feed.mp_name}")
        
        print(f"\n5. 查看分配记录:")
        for alloc_id, allocation in dispatcher.allocations.items():
            print(f"   - {alloc_id}")
            print(f"     节点: {dispatcher.node_statuses[allocation.node_id].node_name}")
            print(f"     状态: {allocation.status}")
    else:
        print("   没有启用的任务")


async def example_child_worker():
    """子节点任务拉取示例"""
    print("="*60)
    print("子节点任务拉取示例")
    print("="*60)
    
    # 初始化
    init_system()
    
    # 检查级联配置
    from core.config import cfg
    cascade_config = cfg.get("cascade", {})
    
    if not cascade_config.get("enabled", False):
        print("错误: 级联模式未启用")
        print("请在config.yaml中配置:")
        print("""
cascade:
  enabled: true
  node_type: child
  parent_api_url: http://parent-server:8001
  api_key: CNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  api_secret: CSxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
""")
        return
    
    if cascade_config.get("node_type") != "child":
        print("错误: 当前节点类型不是child")
        return
    
    print("\n1. 级联配置:")
    print(f"   父节点地址: {cascade_config.get('parent_api_url')}")
    print(f"   API Key: {cascade_config.get('api_key')[:20]}...")
    
    # 检查是否有待处理任务
    print("\n2. 检查待处理任务...")
    from jobs.cascade_sync import cascade_sync_service
    cascade_sync_service.initialize()
    
    task_package = await fetch_task_from_parent()
    if task_package:
        print(f"   找到任务: {task_package.get('task_name')}")
        print(f"   公众号数量: {len(task_package.get('feeds', []))}")
        
        # 执行任务
        print("\n3. 执行任务...")
        await execute_parent_task(task_package)
    else:
        print("   暂无待处理任务")
        print("\n4. 启动持续监听...")
        print("   (按Ctrl+C停止)")
        await start_child_task_worker(poll_interval=30)


async def example_dispatch_and_execute():
    """完整示例：父节点分发+子节点执行"""
    print("="*60)
    print("完整示例：父节点分发+子节点执行")
    print("="*60)
    
    # 父节点分发任务
    print("\n[父节点] 分发任务...")
    init_system()
    dispatcher = CascadeTaskDispatcher()
    online_count = dispatcher.refresh_node_statuses()
    
    if online_count == 0:
        print("   没有在线子节点")
        return
    
    session = DB.get_session()
    task = session.query(MessageTask).filter(MessageTask.status == 0).first()
    
    if task:
        allocations = dispatcher.dispatch_task_to_children(task)
        print(f"   分配完成: {len(allocations)} 个节点")
        
        # 等待子节点处理
        print("\n[等待子节点处理...]")
        await asyncio.sleep(5)
        
        # 子节点拉取并执行（模拟）
        print("\n[子节点] 拉取并执行任务...")
        await example_child_worker()


def example_check_allocation():
    """查看任务分配情况示例"""
    print("="*60)
    print("查看任务分配情况")
    print("="*60)
    
    init_system()
    
    from jobs.cascade_task_dispatcher import cascade_task_dispatcher
    
    # 刷新节点状态
    cascade_task_dispatcher.refresh_node_statuses()
    
    print("\n节点状态:")
    for node_id, status in cascade_task_dispatcher.node_statuses.items():
        print(f"\n{status.node_name} ({status.node_id})")
        print(f"  状态: {'在线' if status.is_online else '离线'}")
        print(f"  容量: {status.current_tasks}/{status.max_capacity}")
        print(f"  API地址: {status.api_url}")
    
    print("\n分配记录:")
    if cascade_task_dispatcher.allocations:
        for alloc_id, allocation in cascade_task_dispatcher.allocations.items():
            node_name = cascade_task_dispatcher.node_statuses[allocation.node_id].node_name
            print(f"\n{alloc_id}")
            print(f"  节点: {node_name}")
            print(f"  任务ID: {allocation.task_id}")
            print(f"  公众号数: {len(allocation.feed_ids)}")
            print(f"  状态: {allocation.status}")
            print(f"  创建时间: {allocation.created_at}")
    else:
        print("  暂无分配记录")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("级联任务分发器使用示例")
        print("\n用法:")
        print("  python cascade_task_dispatcher_example.py parent        # 父节点分发示例")
        print("  python cascade_task_dispatcher_example.py child         # 子节点拉取示例")
        print("  python cascade_task_dispatcher_example.py full          # 完整流程示例")
        print("  python cascade_task_dispatcher_example.py check         # 查看分配情况")
        return
    
    command = sys.argv[1]
    
    if command == "parent":
        example_parent_dispatch()
    elif command == "child":
        asyncio.run(example_child_worker())
    elif command == "full":
        asyncio.run(example_dispatch_and_execute())
    elif command == "check":
        example_check_allocation()
    else:
        print(f"未知命令: {command}")


if __name__ == "__main__":
    main()
