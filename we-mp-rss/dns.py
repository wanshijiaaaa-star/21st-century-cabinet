#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量检测 DNS 解析记录脚本

支持功能：
- 批量检测多个域名的 DNS 记录
- 支持多种记录类型：A, AAAA, CNAME, MX, TXT, NS, SOA
- 支持指定自定义 DNS 服务器
- 支持并发检测
- 支持从文件读取域名列表
- 输出 JSON 或表格格式结果

使用方法：
    python dns.py example.com
    python dns.py example.com google.com
    python dns.py -f domains.txt
    python dns.py example.com -t A,MX,TXT
    python dns.py example.com -s 8.8.8.8
    python dns.py example.com -o json
"""

import argparse
import json
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from typing import Optional

try:
    import dns.resolver
    import dns.exception
    HAS_DNSPYTHON = True
except ImportError:
    HAS_DNSPYTHON = False


@dataclass
class DNSRecord:
    """DNS 记录数据结构"""
    domain: str
    record_type: str
    value: str
    ttl: Optional[int] = None


@dataclass
class DNSResult:
    """DNS 查询结果"""
    domain: str
    record_type: str
    records: list
    error: Optional[str] = None
    query_time: float = 0.0


def query_a_record(domain: str, dns_server: Optional[str] = None) -> DNSResult:
    """查询 A 记录（IPv4 地址）"""
    start_time = time.time()
    records = []
    error = None

    if HAS_DNSPYTHON:
        try:
            resolver = dns.resolver.Resolver()
            if dns_server:
                resolver.nameservers = [dns_server]
            answers = resolver.resolve(domain, 'A')
            for rdata in answers:
                records.append(DNSRecord(
                    domain=domain,
                    record_type='A',
                    value=str(rdata),
                    ttl=answers.rrset.ttl if hasattr(answers, 'rrset') else None
                ))
        except dns.exception.DNSException as e:
            error = str(e)
    else:
        try:
            # 使用 socket 进行基本查询
            addr_info = socket.getaddrinfo(domain, None, socket.AF_INET)
            seen = set()
            for info in addr_info:
                ip = info[4][0]
                if ip not in seen:
                    seen.add(ip)
                    records.append(DNSRecord(
                        domain=domain,
                        record_type='A',
                        value=ip
                    ))
        except socket.gaierror as e:
            error = str(e)

    return DNSResult(
        domain=domain,
        record_type='A',
        records=[asdict(r) for r in records],
        error=error,
        query_time=time.time() - start_time
    )


def query_aaaa_record(domain: str, dns_server: Optional[str] = None) -> DNSResult:
    """查询 AAAA 记录（IPv6 地址）"""
    start_time = time.time()
    records = []
    error = None

    if HAS_DNSPYTHON:
        try:
            resolver = dns.resolver.Resolver()
            if dns_server:
                resolver.nameservers = [dns_server]
            answers = resolver.resolve(domain, 'AAAA')
            for rdata in answers:
                records.append(DNSRecord(
                    domain=domain,
                    record_type='AAAA',
                    value=str(rdata),
                    ttl=answers.rrset.ttl if hasattr(answers, 'rrset') else None
                ))
        except dns.exception.DNSException as e:
            error = str(e)
    else:
        try:
            addr_info = socket.getaddrinfo(domain, None, socket.AF_INET6)
            seen = set()
            for info in addr_info:
                ip = info[4][0]
                if ip not in seen:
                    seen.add(ip)
                    records.append(DNSRecord(
                        domain=domain,
                        record_type='AAAA',
                        value=ip
                    ))
        except socket.gaierror as e:
            error = str(e)

    return DNSResult(
        domain=domain,
        record_type='AAAA',
        records=[asdict(r) for r in records],
        error=error,
        query_time=time.time() - start_time
    )


def query_cname_record(domain: str, dns_server: Optional[str] = None) -> DNSResult:
    """查询 CNAME 记录（别名）"""
    start_time = time.time()
    records = []
    error = None

    if HAS_DNSPYTHON:
        try:
            resolver = dns.resolver.Resolver()
            if dns_server:
                resolver.nameservers = [dns_server]
            answers = resolver.resolve(domain, 'CNAME')
            for rdata in answers:
                records.append(DNSRecord(
                    domain=domain,
                    record_type='CNAME',
                    value=str(rdata).rstrip('.'),
                    ttl=answers.rrset.ttl if hasattr(answers, 'rrset') else None
                ))
        except dns.exception.DNSException as e:
            error = str(e)
    else:
        error = "需要安装 dnspython 库来查询 CNAME 记录: pip install dnspython"

    return DNSResult(
        domain=domain,
        record_type='CNAME',
        records=[asdict(r) for r in records],
        error=error,
        query_time=time.time() - start_time
    )


def query_mx_record(domain: str, dns_server: Optional[str] = None) -> DNSResult:
    """查询 MX 记录（邮件交换）"""
    start_time = time.time()
    records = []
    error = None

    if HAS_DNSPYTHON:
        try:
            resolver = dns.resolver.Resolver()
            if dns_server:
                resolver.nameservers = [dns_server]
            answers = resolver.resolve(domain, 'MX')
            for rdata in answers:
                records.append(DNSRecord(
                    domain=domain,
                    record_type='MX',
                    value=f"{rdata.preference} {str(rdata.exchange).rstrip('.')}",
                    ttl=answers.rrset.ttl if hasattr(answers, 'rrset') else None
                ))
        except dns.exception.DNSException as e:
            error = str(e)
    else:
        error = "需要安装 dnspython 库来查询 MX 记录: pip install dnspython"

    return DNSResult(
        domain=domain,
        record_type='MX',
        records=[asdict(r) for r in records],
        error=error,
        query_time=time.time() - start_time
    )


def query_txt_record(domain: str, dns_server: Optional[str] = None) -> DNSResult:
    """查询 TXT 记录"""
    start_time = time.time()
    records = []
    error = None

    if HAS_DNSPYTHON:
        try:
            resolver = dns.resolver.Resolver()
            if dns_server:
                resolver.nameservers = [dns_server]
            answers = resolver.resolve(domain, 'TXT')
            for rdata in answers:
                txt_data = ''.join(s.decode() for s in rdata.strings)
                records.append(DNSRecord(
                    domain=domain,
                    record_type='TXT',
                    value=txt_data,
                    ttl=answers.rrset.ttl if hasattr(answers, 'rrset') else None
                ))
        except dns.exception.DNSException as e:
            error = str(e)
    else:
        error = "需要安装 dnspython 库来查询 TXT 记录: pip install dnspython"

    return DNSResult(
        domain=domain,
        record_type='TXT',
        records=[asdict(r) for r in records],
        error=error,
        query_time=time.time() - start_time
    )


def query_ns_record(domain: str, dns_server: Optional[str] = None) -> DNSResult:
    """查询 NS 记录（域名服务器）"""
    start_time = time.time()
    records = []
    error = None

    if HAS_DNSPYTHON:
        try:
            resolver = dns.resolver.Resolver()
            if dns_server:
                resolver.nameservers = [dns_server]
            answers = resolver.resolve(domain, 'NS')
            for rdata in answers:
                records.append(DNSRecord(
                    domain=domain,
                    record_type='NS',
                    value=str(rdata).rstrip('.'),
                    ttl=answers.rrset.ttl if hasattr(answers, 'rrset') else None
                ))
        except dns.exception.DNSException as e:
            error = str(e)
    else:
        error = "需要安装 dnspython 库来查询 NS 记录: pip install dnspython"

    return DNSResult(
        domain=domain,
        record_type='NS',
        records=[asdict(r) for r in records],
        error=error,
        query_time=time.time() - start_time
    )


def query_soa_record(domain: str, dns_server: Optional[str] = None) -> DNSResult:
    """查询 SOA 记录（授权起始）"""
    start_time = time.time()
    records = []
    error = None

    if HAS_DNSPYTHON:
        try:
            resolver = dns.resolver.Resolver()
            if dns_server:
                resolver.nameservers = [dns_server]
            answers = resolver.resolve(domain, 'SOA')
            for rdata in answers:
                records.append(DNSRecord(
                    domain=domain,
                    record_type='SOA',
                    value=f"{rdata.mname.rstrip('.')} {rdata.rname.rstrip('.')} {rdata.serial} {rdata.refresh} {rdata.retry} {rdata.expire} {rdata.minimum}",
                    ttl=answers.rrset.ttl if hasattr(answers, 'rrset') else None
                ))
        except dns.exception.DNSException as e:
            error = str(e)
    else:
        error = "需要安装 dnspython 库来查询 SOA 记录: pip install dnspython"

    return DNSResult(
        domain=domain,
        record_type='SOA',
        records=[asdict(r) for r in records],
        error=error,
        query_time=time.time() - start_time
    )


# 记录类型与查询函数的映射
QUERY_FUNCTIONS = {
    'A': query_a_record,
    'AAAA': query_aaaa_record,
    'CNAME': query_cname_record,
    'MX': query_mx_record,
    'TXT': query_txt_record,
    'NS': query_ns_record,
    'SOA': query_soa_record,
}


def check_domain(domain: str, record_types: list, dns_server: Optional[str] = None) -> list:
    """检查单个域名的多种记录类型"""
    results = []
    for rtype in record_types:
        rtype = rtype.upper()
        if rtype in QUERY_FUNCTIONS:
            result = QUERY_FUNCTIONS[rtype](domain, dns_server)
            results.append(asdict(result))
        else:
            results.append(asdict(DNSResult(
                domain=domain,
                record_type=rtype,
                records=[],
                error=f"不支持的记录类型: {rtype}"
            )))
    return results


def check_domains_batch(domains: list, record_types: list, dns_server: Optional[str] = None, 
                        max_workers: int = 10) -> dict:
    """批量检查多个域名"""
    all_results = {}
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_domain = {
            executor.submit(check_domain, domain, record_types, dns_server): domain
            for domain in domains
        }
        
        for future in as_completed(future_to_domain):
            domain = future_to_domain[future]
            try:
                results = future.result()
                all_results[domain] = results
            except Exception as e:
                all_results[domain] = [asdict(DNSResult(
                    domain=domain,
                    record_type='ALL',
                    records=[],
                    error=f"查询失败: {str(e)}"
                ))]
    
    return all_results


def read_domains_from_file(filepath: str) -> list:
    """从文件读取域名列表"""
    domains = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                domain = line.strip()
                # 跳过空行和注释行
                if domain and not domain.startswith('#'):
                    # 移除可能的 http:// 或 https:// 前缀
                    domain = domain.replace('http://', '').replace('https://', '')
                    # 移除路径部分
                    domain = domain.split('/')[0]
                    domains.append(domain)
    except FileNotFoundError:
        print(f"错误: 文件 '{filepath}' 不存在")
        sys.exit(1)
    except Exception as e:
        print(f"读取文件错误: {e}")
        sys.exit(1)
    return domains


def print_table(results: dict):
    """以表格格式输出结果"""
    print("\n" + "=" * 80)
    print(f"{'域名':<30} {'类型':<8} {'记录值':<40}")
    print("=" * 80)
    
    for domain, domain_results in results.items():
        first_row = True
        for result in domain_results:
            if result['records']:
                for i, record in enumerate(result['records']):
                    domain_display = domain if (first_row and i == 0) else ''
                    type_display = result['record_type'] if (i == 0) else ''
                    value = record['value'][:38] + '..' if len(record['value']) > 40 else record['value']
                    print(f"{domain_display:<30} {type_display:<8} {value:<40}")
                    if i == 0 and result['records']:
                        first_row = False
            elif result['error']:
                domain_display = domain if first_row else ''
                print(f"{domain_display:<30} {result['record_type']:<8} [错误] {result['error'][:30]}")
                first_row = False
            else:
                domain_display = domain if first_row else ''
                print(f"{domain_display:<30} {result['record_type']:<8} [无记录]")
                first_row = False
        print("-" * 80)


def print_summary(results: dict):
    """输出统计摘要"""
    total_domains = len(results)
    total_queries = sum(len(v) for v in results.values())
    success_queries = sum(1 for v in results.values() for r in v if r['records'])
    error_queries = sum(1 for v in results.values() for r in v if r['error'])
    total_time = sum(r['query_time'] for v in results.values() for r in v)
    
    print("\n" + "=" * 80)
    print("统计摘要")
    print("=" * 80)
    print(f"检测域名数: {total_domains}")
    print(f"查询总次数: {total_queries}")
    print(f"成功查询: {success_queries}")
    print(f"失败查询: {error_queries}")
    print(f"总耗时: {total_time:.2f} 秒")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description='批量检测 DNS 解析记录',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python dns.py example.com
    python dns.py example.com google.com
    python dns.py -f domains.txt
    python dns.py example.com -t A,MX,TXT
    python dns.py example.com -s 8.8.8.8
    python dns.py example.com -o json
    python dns.py example.com -w 20
    # 使用前缀和后缀批量生成域名
    python dns.py --suffix example.com --prefix www,api,blog
    python dns.py --suffix example.com --prefix-file prefixes.txt
    # 直接检测所有子域名
    python dns.py www.example.com api.example.com blog.example.com
        """
    )
    
    parser.add_argument('domains', nargs='*', help='要检测的域名列表')
    parser.add_argument('-f', '--file', help='从文件读取域名列表（每行一个域名）')
    parser.add_argument('--suffix', '-S', help='统一域名后缀，与 --prefix 或 --prefix-file 配合使用')
    parser.add_argument('--prefix', '-P', help='域名前缀列表，多个用逗号分隔，如: www,api,blog')
    parser.add_argument('--prefix-file', '-PF', help='从文件读取域名前缀列表（每行一个）')
    parser.add_argument('-t', '--types', default='A', 
                        help='DNS 记录类型，多个用逗号分隔 (默认: A)，支持: A,AAAA,CNAME,MX,TXT,NS,SOA')
    parser.add_argument('-s', '--server', help='指定 DNS 服务器地址')
    parser.add_argument('-o', '--output', choices=['table', 'json'], default='table',
                        help='输出格式 (默认: table)')
    parser.add_argument('-w', '--workers', type=int, default=10,
                        help='并发工作线程数 (默认: 10)')
    parser.add_argument('--summary', action='store_true', help='显示统计摘要')
    
    args = parser.parse_args()
    
    # 收集域名
    domains = list(args.domains)
    if args.file:
        domains.extend(read_domains_from_file(args.file))
    
    # 处理前缀+后缀生成域名
    if args.suffix:
        suffix = args.suffix.strip().lstrip('.')
        prefixes = []
        
        # 从命令行获取前缀
        if args.prefix:
            prefixes.extend([p.strip() for p in args.prefix.split(',') if p.strip()])
        
        # 从文件读取前缀
        if args.prefix_file:
            try:
                with open(args.prefix_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        prefix = line.strip()
                        if prefix and not prefix.startswith('#'):
                            prefixes.append(prefix)
            except FileNotFoundError:
                print(f"错误: 前缀文件 '{args.prefix_file}' 不存在")
                sys.exit(1)
        
        # 生成域名
        if prefixes:
            for prefix in prefixes:
                if prefix in ('@', ''):
                    # @ 或空前缀表示根域名
                    domains.append(suffix)
                else:
                    domains.append(f"{prefix}.{suffix}")
        else:
            # 只有后缀没有前缀，只检测根域名
            domains.append(suffix)
    
    if not domains:
        parser.print_help()
        print("\n错误: 请提供至少一个域名，或使用以下方式之一：")
        print("  - 直接指定域名: python dns.py example.com")
        print("  - 从文件读取: python dns.py -f domains.txt")
        print("  - 前缀+后缀: python dns.py --suffix example.com --prefix www,api")
        sys.exit(1)
    
    # 解析记录类型
    record_types = [t.strip().upper() for t in args.types.split(',')]
    
    # 检查 dnspython 库
    if not HAS_DNSPYTHON:
        unsupported = [t for t in record_types if t != 'A' and t != 'AAAA']
        if unsupported:
            print(f"警告: 检测到未安装 dnspython 库，以下记录类型将无法查询: {', '.join(unsupported)}")
            print("建议安装: pip install dnspython")
            print()
    
    # 输出配置信息
    print(f"\nDNS 解析检测工具")
    print(f"{'=' * 40}")
    print(f"域名数量: {len(domains)}")
    print(f"记录类型: {', '.join(record_types)}")
    print(f"DNS 服务器: {args.server or '系统默认'}")
    print(f"并发线程: {args.workers}")
    print(f"{'=' * 40}\n")
    
    # 执行检测
    results = check_domains_batch(domains, record_types, args.server, args.workers)
    
    # 输出结果
    if args.output == 'json':
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print_table(results)
    
    # 输出摘要
    if args.summary:
        print_summary(results)


if __name__ == '__main__':
    main()
