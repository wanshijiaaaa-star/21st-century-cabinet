#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据分析脚本（简化版） - 不依赖pandas
提取公众号名称并将其他列用|连接
使用方法: python tools/import.py
输出: data/processed_output.txt
"""
import random
import os
import sys
from time import sleep

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def process_text_file(file_path: str) -> list:
    """处理制表符分隔的文本文件"""
    results = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                # 按制表符分割
                parts = line.split('\t')
                
                # 确保至少有两列（序号和公众号名称）
                if len(parts) >= 2:
                    # 第二列是公众号名称（索引1）
                    public_name = parts[0 ].strip()
                    # 后面的列用|连接
                    other_columns = [p.strip() for p in parts[1:] if p.strip()]
                    
                    if public_name:
                        if other_columns:
                            result = f"{public_name}|{'|'.join(other_columns)}"
                        else:
                            result = public_name
                        results.append(result)
                else:
                    print(f"警告: 第{line_num}行数据格式不正确，跳过")
        
        return results
    except Exception as e:
        print(f"读取文件失败 {file_path}: {e}")
        return []


def import_mps(data_file:str="./data/data1.txt"):
    if not os.path.exists(data_file):
        print(f"错误: 未找到数据文件: {data_file}")
        print("请确保data目录下存在data.txt文件")
        sys.exit(1)
    
    print(f"正在处理文件: {data_file}")
    print("=" * 50)
    
    # 处理数据
    results = process_text_file(data_file)
    
    if results:
        print(f"\n处理成功，共 {len(results)} 条记录")
        print("\n前10条结果:")
        for i, result in enumerate(results[:10], 1):
            print(f"{i}. {result}")
        
        if len(results) > 10:
            print(f"... 还有 {len(results) - 10} 条记录未显示")
        
        # 通过搜索接口获取相关信息并添加到feeds表
        print("\n" + "=" * 50)
        print("正在通过搜索接口获取公众号信息...")
        
        from core.db import DB
        from core.models.feed import Feed
        from core.wx import search_Biz
        from datetime import datetime
        import base64
        import time
        
        session = DB.get_session()
        success_count = 0
        skip_count = 0
        error_count = 0
        failed_list = []  # 记录失败的账号
        
        for result in results:
            mp_name = result.split('|')[0].strip() if '|' in result else result.strip()
            
            try:
                # 搜索公众号
                print(f"正在搜索: {mp_name}")
                # 检查是否已存在
                existing_feed = session.query(Feed).filter(Feed.mp_name == mp_name).first()
                
                if existing_feed:
                    print(f"  → 已存在，跳过: {mp_name}")
                    skip_count += 1
                    continue
                search_result = search_Biz(mp_name, limit=1, offset=0)
                mp_info=None
                if search_result and 'list' in search_result and len(search_result['list']) > 0:
                    items=[]
                    for item in search_result['list']:
                        print(item)
                        items.append(item.get("nickname"))
                        if item.get("nickname") == mp_name:
                            mp_info = item
                    if mp_info is None:
                        raise ValueError(f"类似的结果:{items}")
                    # 提取公众号信息
                    mp_id = mp_info.get('fakeid', '')
                    mp_cover = mp_info.get('round_head_img', '')
                    mp_intro = mp_info.get('signature', '')
                    
                    
                    
                    # 解码mp_id
                    mpx_id = base64.b64decode(mp_id).decode("utf-8")
                    now = datetime.now()
                    
                    # 创建新的Feed记录
                    new_feed = Feed(
                        id=f"MP_WXS_{mpx_id}",
                        mp_name=mp_name,
                        mp_cover=mp_cover,
                        mp_intro=mp_intro,
                        status=1,
                        created_at=now,
                        updated_at=now,
                        faker_id=mp_id,
                        update_time=0,
                        sync_time=0,
                    )
                    session.add(new_feed)
                    session.commit()
                    print(f"  ✓ 添加成功: {mp_name}")
                    success_count += 1
                    
                    # 添加延迟避免频繁请求
                    time.sleep(random.randint(1, 3))
                else:
                    print(f"  ✗ 未找到: {mp_name}")
                    failed_list.append(mp_name)
                    error_count += 1
                    
            except Exception as e:
                print(f"  ✗ 处理失败 {mp_name}: {str(e)}")
                failed_list.append(f"{mp_name} (错误: {str(e)})")
                error_count += 1
                session.rollback()
                if "frequencey control" in str(e):
                    sleep(random.randint(30, 60))
        
        print("\n" + "=" * 50)
        print(f"导入完成: 成功 {success_count} 条，跳过 {skip_count} 条，失败 {error_count} 条")
        print("=" * 50)

        # 保存失败列表到文件
        if failed_list:
            failed_file = f"{data_file.replace('.txt', '')}_failed.txt"
            with open(failed_file, 'w', encoding='utf-8') as f:
                f.write("导入失败的账号列表\n")
                f.write("=" * 50 + "\n")
                for idx, account in enumerate(failed_list, 1):
                    f.write(f"{idx}. {account}\n")
            print(f"\n失败列表已保存到: {failed_file}")
            print(f"共 {len(failed_list)} 个失败账号")
        
    else:
        print("未生成任何结果")

if __name__ == '__main__':
    data_file = "./data/data1.txt"
    if len(sys.argv) > 1:
        data_file = sys.argv[1]
    import_mps(data_file)