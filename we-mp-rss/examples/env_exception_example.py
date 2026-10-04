#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""环境异常统计功能测试示例"""

from core.redis_client import record_env_exception, get_env_exception_stats
from datetime import datetime, timedelta


def test_record_exception():
    """测试记录环境异常"""
    # 模拟记录环境异常
    test_url = "https://mp.weixin.qq.com/s/test123"
    test_mp_name = "测试公众号"
    test_mp_id = "MP_WXS_test123"
    
    success = record_env_exception(
        url=test_url,
        mp_name=test_mp_name,
        mp_id=test_mp_id
    )
    
    if success:
        print(f"✓ 成功记录环境异常: {test_url}")
    else:
        print("✗ 记录失败，请检查 Redis 配置")


def test_get_stats():
    """测试获取统计信息"""
    # 获取今日统计
    today = datetime.now().strftime("%Y-%m-%d")
    stats = get_env_exception_stats(today)
    
    print("\n=== 今日环境异常统计 ===")
    print(f"日期: {stats.get('date', 'N/A')}")
    print(f"总次数: {stats.get('total', 0)}")
    
    if 'urls' in stats and stats['urls']:
        print(f"\n异常URL数量: {len(stats['urls'])}")
        for url, timestamp in list(stats['urls'].items())[:3]:
            print(f"  - {url}: {timestamp}")
    
    if 'mp_stats' in stats and stats['mp_stats']:
        print(f"\n公众号维度统计:")
        for mp_id, count in stats['mp_stats'].items():
            print(f"  - {mp_id}: {count} 次")


def test_historical_stats():
    """测试历史统计查询"""
    # 获取过去7天的统计
    print("\n=== 过去7天环境异常统计 ===")
    
    for i in range(7):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        stats = get_env_exception_stats(date)
        total = stats.get('total', 0)
        
        if total > 0:
            print(f"{date}: {total} 次")


def test_api_usage():
    """演示如何通过API获取统计"""
    print("\n=== API 使用示例 ===")
    print("可以通过以下API接口获取统计信息:")
    print()
    print("1. 获取今日统计:")
    print("   GET /api/env-exception/today")
    print()
    print("2. 获取指定日期统计:")
    print("   GET /api/env-exception/stats?date=2024-01-01")
    print()
    print("注意: 需要在请求头中包含有效的 Authorization")


if __name__ == "__main__":
    print("=" * 60)
    print("环境异常统计功能测试")
    print("=" * 60)
    
    # 测试记录异常
    test_record_exception()
    
    # 测试获取统计
    test_get_stats()
    
    # 测试历史统计
    test_historical_stats()
    
    # 演示API使用
    test_api_usage()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
