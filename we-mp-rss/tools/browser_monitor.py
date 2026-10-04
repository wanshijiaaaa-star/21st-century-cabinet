#!/usr/bin/env python3
"""
浏览器资源监控工具

用于检测和监控未关闭的浏览器进程，帮助识别资源泄漏问题
"""

import psutil
import os
import sys
import time
from datetime import datetime
from typing import List, Dict

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.print import print_info, print_warning, print_error, print_success
except ImportError:
    # 如果无法导入，使用简单的打印函数
    def print_info(msg): print(f"[INFO] {msg}")
    def print_warning(msg): print(f"[WARNING] {msg}")  
    def print_error(msg): print(f"[ERROR] {msg}")
    def print_success(msg): print(f"[SUCCESS] {msg}")

class BrowserMonitor:
    """浏览器进程监控器"""
    
    BROWSER_PROCESS_NAMES = [
        'chrome', 'chromium', 'firefox', 'msedge', 
        'webkit', 'playwright', 'node'
    ]
    
    def __init__(self):
        self.current_process = psutil.Process()
        self.initial_browser_count = self.get_browser_process_count()
        
    def get_browser_processes(self) -> List[Dict]:
        """获取所有浏览器进程信息"""
        browser_processes = []
        
        try:
            # 获取当前进程的所有子进程
            children = self.current_process.children(recursive=True)
            
            for proc in children:
                try:
                    proc_name = proc.name().lower()
                    # 检查是否为浏览器相关进程
                    if any(browser in proc_name for browser in self.BROWSER_PROCESS_NAMES):
                        browser_processes.append({
                            'pid': proc.pid,
                            'name': proc.name(),
                            'status': proc.status(),
                            'memory': proc.memory_info().rss / 1024 / 1024,  # MB
                            'cpu_percent': proc.cpu_percent(),
                            'create_time': datetime.fromtimestamp(proc.create_time()),
                            'cmdline': ' '.join(proc.cmdline()) if proc.cmdline() else ''
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except psutil.NoSuchProcess:
            pass
            
        return browser_processes
    
    def get_browser_process_count(self) -> int:
        """获取浏览器进程数量"""
        return len(self.get_browser_processes())
    
    def print_status(self):
        """打印当前浏览器状态"""
        processes = self.get_browser_processes()
        count = len(processes)
        
        print_info(f"浏览器进程监控报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print_info("=" * 60)
        print_info(f"当前浏览器进程数: {count}")
        print_info(f"初始浏览器进程数: {self.initial_browser_count}")
        print_info(f"进程增长: {count - self.initial_browser_count}")
        
        if processes:
            print_warning("\n浏览器进程详情:")
            for proc in processes:
                print_warning(f"  PID: {proc['pid']:<8} 名称: {proc['name']:<12} "
                            f"内存: {proc['memory']:.1f}MB "
                            f"状态: {proc['status']:<10}")
                if proc['cmdline']:
                    print_warning(f"    命令: {proc['cmdline'][:100]}...")
        else:
            print_success("✅ 未发现残留的浏览器进程")
    
    def check_resource_leak(self) -> bool:
        """检查是否存在资源泄漏"""
        current_count = self.get_browser_process_count()
        if current_count > self.initial_browser_count + 2:  # 允许2个进程的正常增长
            print_warning(f"⚠️  检测到可能的浏览器资源泄漏!")
            print_warning(f"进程数从 {self.initial_browser_count} 增长到 {current_count}")
            return True
        return False
    
    def force_cleanup_browser_processes(self):
        """强制清理浏览器进程（谨慎使用）"""
        processes = self.get_browser_processes()
        if not processes:
            print_info("没有需要清理的浏览器进程")
            return
            
        print_warning(f"准备清理 {len(processes)} 个浏览器进程...")
        
        for proc in processes:
            try:
                p = psutil.Process(proc['pid'])
                print_info(f"终止进程: PID {proc['pid']} ({proc['name']})")
                p.terminate()
                
                # 等待进程终止
                try:
                    p.wait(timeout=5)
                    print_success(f"成功终止进程 {proc['pid']}")
                except psutil.TimeoutExpired:
                    print_warning(f"进程 {proc['pid']} 未响应，强制终止...")
                    p.kill()
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                print_error(f"无法终止进程 {proc['pid']}: {e}")

def monitor_browser_resources(interval: int = 30, duration: int = 300):
    """持续监控浏览器资源
    
    Args:
        interval: 监控间隔（秒）
        duration: 监控持续时间（秒）
    """
    monitor = BrowserMonitor()
    
    print_info(f"开始监控浏览器资源，间隔 {interval}s，持续 {duration}s")
    monitor.print_status()
    
    start_time = time.time()
    
    while time.time() - start_time < duration:
        time.sleep(interval)
        print_info(f"\n--- 监控间隔 {interval}s ---")
        monitor.print_status()
        
        if monitor.check_resource_leak():
            print_warning("检测到资源泄漏，请检查代码中的浏览器管理逻辑")

def main():
    """主函数"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "monitor":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            duration = int(sys.argv[3]) if len(sys.argv) > 3 else 300
            monitor_browser_resources(interval, duration)
            
        elif command == "status":
            monitor = BrowserMonitor()
            monitor.print_status()
            
        elif command == "cleanup":
            confirm = input("确定要清理所有浏览器进程吗？(y/N): ").lower().strip()
            if confirm == 'y' or confirm == 'yes':
                monitor = BrowserMonitor()
                monitor.force_cleanup_browser_processes()
            else:
                print_info("已取消清理操作")
                
        else:
            print_usage()
    else:
        print_usage()

def print_usage():
    """打印使用说明"""
    print_info("浏览器资源监控工具")
    print_info("使用方法:")
    print_info("  python browser_monitor.py status      # 显示当前状态")
    print_info("  python browser_monitor.py monitor    # 持续监控（默认30s间隔，5分钟）")
    print_info("  python browser_monitor.py cleanup     # 强制清理浏览器进程")
    print_info("")
    print_info("示例:")
    print_info("  python browser_monitor.py monitor 60 600  # 60s间隔，监控10分钟")

if __name__ == "__main__":
    main()