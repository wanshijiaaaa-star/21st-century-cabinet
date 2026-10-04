"""验证级联任务分发系统的导入是否正常"""

import sys
import os

def test_imports():
    """测试所有必要的导入"""
    print("="*60)
    print("验证级联任务分发系统导入")
    print("="*60)
    print()

    # 测试结果
    results = []

    # 测试1: core模块导入
    print("1. 测试 core 模块导入...")
    try:
        from core.db import DB
        from core.models.cascade_node import CascadeNode
        from core.models.message_task import MessageTask
        from core.models.feed import Feed
        from core.cascade import CascadeManager, cascade_manager
        from core.print import print_info, print_success, print_error, print_warning
        print("   ✓ core 模块导入成功")
        results.append(True)
    except Exception as e:
        print(f"   ✗ core 模块导入失败: {str(e)}")
        results.append(False)

    # 测试2: jobs模块导入
    print("\n2. 测试 jobs.cascade_task_dispatcher 导入...")
    try:
        from jobs.cascade_task_dispatcher import (
            CascadeTaskDispatcher,
            cascade_task_dispatcher,
            TaskAllocation,
            NodeStatus
        )
        print("   ✓ cascade_task_dispatcher 导入成功")
        results.append(True)
    except Exception as e:
        print(f"   ✗ cascade_task_dispatcher 导入失败: {str(e)}")
        results.append(False)

    # 测试3: 创建分发器实例
    print("\n3. 测试创建分发器实例...")
    try:
        dispatcher = CascadeTaskDispatcher()
        print(f"   ✓ 分发器创建成功")
        print(f"     - allocations: {len(dispatcher.allocations)}")
        print(f"     - node_statuses: {len(dispatcher.node_statuses)}")
        results.append(True)
    except Exception as e:
        print(f"   ✗ 分发器创建失败: {str(e)}")
        results.append(False)

    # 测试4: 测试API导入
    print("\n4. 测试 API 模块导入...")
    try:
        from apis.cascade import router
        print("   ✓ cascade API 导入成功")
        results.append(True)
    except Exception as e:
        print(f"   ✗ cascade API 导入失败: {str(e)}")
        results.append(False)

    # 测试5: 测试cascade_sync导入
    print("\n5. 测试 jobs.cascade_sync 导入...")
    try:
        from jobs.cascade_sync import CascadeSyncService, cascade_sync_service
        print("   ✓ cascade_sync 导入成功")
        results.append(True)
    except Exception as e:
        print(f"   ✗ cascade_sync 导入失败: {str(e)}")
        results.append(False)

    # 总结
    print()
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"测试结果: {passed}/{total} 通过")
    print("="*60)

    if passed == total:
        print("\n✓ 所有测试通过！系统可以正常使用。")
        return True
    else:
        print(f"\n✗ 有 {total - passed} 个测试失败，请检查错误信息。")
        return False


def main():
    """主函数"""
    success = test_imports()

    if success:
        print("\n下一步:")
        print("  1. 运行: python test_cascade_task_dispatcher.py")
        print("  2. 运行: python examples/cascade_task_dispatcher_example.py check")
        print("  3. 参考: docs/CASCADE_TASK_DISPATCHER.md")
    else:
        print("\n故障排查:")
        print("  1. 确保在项目根目录下运行")
        print("  2. 检查 Python 路径配置")
        print("  3. 确认所有依赖已安装")


if __name__ == "__main__":
    main()
