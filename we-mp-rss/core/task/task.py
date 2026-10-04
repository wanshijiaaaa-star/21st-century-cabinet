import threading
import random
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Callable, Any, Optional
from core.log import logger
import uuid
# 设置日志

class TaskScheduler:
    """
    线程调度器类，支持cron定时任务调度
    使用APScheduler作为底层调度引擎

    Cron表达式说明:
    一个cron表达式有5个或6个空格分隔的时间字段，格式为:
        ┌───────────── 秒 (0 - 59) (6位格式)
        │ ┌───────────── 分钟 (0 - 59)
        │ │ ┌───────────── 小时 (0 - 23)
        │ │ │ ┌───────────── 日 (1 - 31)
        │ │ │ │ ┌───────────── 月 (1 - 12 或 JAN-DEC)
        │ │ │ │ │ ┌───────────── 星期 (0 - 6 或 SUN-SAT，0是周日)
        │ │ │ │ │ │
        * * * * * *
        或
        * * * * * (5位格式)

    特殊字符:
        *   任意值
        ,   值列表分隔符 (如 "MON,WED,FRI")
        -   范围 (如 "9-17" 表示9点到17点)
        /   步长 (如 "0/15" 表示从0开始每15分钟)
        ?   日或星期字段无特定值 (只能用在日或星期字段)

    常用示例:
        "0 0 * * *"     每天午夜执行 (5位)
        "0 9 * * MON"   每周一上午9点执行 (5位)
        "0 */6 * * *"   每6小时执行一次 (5位)
        "0 9-17 * * MON-FRI" 工作日每小时从9点到17点执行 (5位)
        "0 0 1 * *"     每月第一天午夜执行 (5位)
        "0 0 1 1 *"     每年1月1日午夜执行 (5位)
        "30 * * * * *"  每分钟的第30秒执行 (6位)
        "0 0 0 * * *"   每天午夜执行 (6位)
        "0 0 9 * * MON" 每周一上午9点执行 (6位)
    """
    
    def __init__(self):
        """初始化调度器和线程锁"""
        self._scheduler = BackgroundScheduler()
        self._lock = threading.Lock()
        self._jobs = {}

    def add_cron_job(self,
                     func: Callable,
                     cron_expr: str,
                     args: Optional[dict] = None,
                     kwargs: Optional[dict] = None,
                     job_id: Optional[str] = None,
                     tag: str = ""
                     ) -> str:
        """
        添加一个cron定时任务
        
        :param func: 要执行的函数
        :param cron_expr: cron表达式，如"* * * * *"
        :param args: 函数的位置参数
        :param kwargs: 函数的关键字参数
        :param job_id: 任务ID，如果不指定则自动生成
        :return: 任务ID
        """
        with self._lock:
            try:
                logger.info(f"Adding cron job with expression: {cron_expr}")
                
                # 解析cron表达式为各个字段
                fields = cron_expr.split()
                if len(fields) == 5:
                    # 5位格式: 分 时 日 月 周
                    minute, hour, day, month, day_of_week = fields
                    second = "0"  # 默认秒为0
                elif len(fields) == 6:
                    # 6位格式: 秒 分 时 日 月 周
                    second, minute, hour, day, month, day_of_week = fields
                else:
                    error_msg = f"Invalid cron expression: {cron_expr}. Expected 5 or 6 fields."
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                # 处理随机时间范围
                def parse_random_field(field: str, field_name: str):
                    # 假设我们要解析的格式是 "*/1~3" 或 "1~3-3~10"
                    import re
                    try:
                        # 使用正则表达式匹配格式
                        pattern = r'(\d+)\~(\d+)'
                        match = re.findall(pattern, field)
                        if match:
                            # 提取匹配的组
                            start, end = match[0]
                            step = random.randint(int(start), int(end))
                            field = field.replace(f"{start}~{end}", str(step))
                    except:
                        pass
                    return field

                second = parse_random_field(second, 'second')
                minute = parse_random_field(minute, 'minute')
                hour = parse_random_field(hour, 'hour')
                day = parse_random_field(day, 'day')
                month = parse_random_field(month, 'month')
                day_of_week_original = parse_random_field(day_of_week, 'day_of_week')

                def translate_day_of_week(dow_str: str) -> str:
                    """将标准cron的星期(0=周日)转换为APScheduler的星期(0=周一)"""
                    import re
                    # 如果字段是 "*" 或 "?"，或者包含字母，则不处理
                    if not re.search(r'\d', dow_str) or re.search(r'[a-zA-Z]', dow_str):
                        return dow_str

                    def replacer(match):
                        num = int(match.group(0))
                        if num == 0:
                            return '6'
                        elif num == 7:  # 标准cron的周日别名 (兼容)
                            return '6'
                        else:
                            return str(num - 1)

                    return re.sub(r'\d+', replacer, dow_str)

                day_of_week = translate_day_of_week(day_of_week_original)

                # 生成job_id
                job_id = job_id or str(uuid.uuid4())

                trigger = CronTrigger(
                    second=second,
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week
                )
                
                # 包装任务函数以捕获异常
                def wrapped_func(*args, **kwargs):
                    try:
                        # logger.info(f"Executing job {job_id or 'anonymous'}")
                        return func(*args, **kwargs)
                    except Exception as e:
                        logger.error(f"Job {tag} {job_id or 'anonymous'} failed: {str(e)}")
                        raise
                
                job = self._scheduler.add_job(
                    wrapped_func,
                    trigger=trigger,
                    args=args,
                    kwargs=kwargs,
                    id=str(job_id),
                    max_instances=1,          # 同一任务最多1个实例
                    coalesce=True,            # 错过的任务合并
                    misfire_grace_time=300    # 5分钟宽限时间
                )
                self._jobs[job.id] = job
                logger.info(f"Successfully added job {tag} {job.id}")
                return job.id
            except Exception as e:
                logger.error(f"Failed to add cron job: {str(e)}")
                raise
    
    def remove_job(self, job_id: str) -> bool:
        """
        移除指定任务
        
        :param job_id: 要移除的任务ID
        :return: 是否成功移除
        """
        with self._lock:
            if job_id in self._jobs:
                self._scheduler.remove_job(job_id)
                del self._jobs[job_id]
                return True
            return False
    
    def clear_all_jobs(self) -> int:
        """
        清除所有任务，包括正在运行的任务
        
        :return: 被删除的任务数量
        """
        with self._lock:
            job_count = len(self._jobs)
            if job_count > 0:
                # 先终止所有正在运行的任务
                for job in self._scheduler.get_jobs():
                    try:
                        self._scheduler.remove_job(job.id)
                    except Exception as e:
                        logger.warning(f"Failed to remove job {job.id}: {str(e)}")
                
                # 清除所有计划任务
                self._scheduler.remove_all_jobs()
                self._jobs.clear()
                logger.info(f"Removed all {job_count} jobs")
            return job_count
    
    def start(self) -> None:
        """启动调度器"""
        with self._lock:
            if self._scheduler.running:
                logger.warning("Scheduler is already running")
                return
                
            try:
                logger.info("Starting scheduler...")
                self._scheduler.start()
                logger.info("Scheduler started successfully")
            except Exception as e:
                logger.error(f"Failed to start scheduler: {str(e)}")
                raise
    
    def shutdown(self, wait: bool = True) -> None:
        """
        关闭调度器
        
        :param wait: 是否等待所有任务完成
        """
        with self._lock:
            if self._scheduler.running:
                self._scheduler.shutdown(wait=wait)
                self._jobs.clear()
    
    def get_job_ids(self) -> list[str]:
        """获取所有任务ID"""
        with self._lock:
            return list(self._jobs.keys())
    
    def __enter__(self):
        """支持上下文管理协议"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持上下文管理协议"""
        self.shutdown()

    def get_scheduler_status(self) -> dict:
        """
        获取调度器状态信息
        
        :return: 包含调度器状态的字典
        """
        with self._lock:
            next_run_times = []
            # 从调度器获取实时 Job 信息
            for job in self._scheduler.get_jobs():
                try:
                    next_time = getattr(job, 'next_run_time', None)
                    next_run_times.append((
                        job.id,
                        next_time.isoformat() if next_time else None
                    ))
                except Exception as e:
                    logger.warning(f"Failed to get next_run_time for job {job.id}: {e}")
                    next_run_times.append((job.id, None))
            
            return {
                'running': self._scheduler.running,
                'job_count': len(self._jobs),
                'next_run_times': next_run_times
            }

    def get_job_details(self, job_id: str) -> dict:
        """
        获取任务详细信息
        
        :param job_id: 任务ID
        :return: 包含任务详情的字典
        """
        with self._lock:
            if job_id not in self._jobs:
                raise ValueError(f"Job {job_id} not found")
            
            # 从调度器获取实时 Job 信息
            job = self._scheduler.get_job(job_id)
            if not job:
                # 如果调度器中没有，返回基本信息
                return {
                    'id': job_id,
                    'name': job_id,
                    'trigger': '',
                    'next_run_time': None,
                    'last_run_time': None,
                }
            
            return {
                'id': job.id,
                'name': getattr(job, 'name', job_id),
                'trigger': str(job.trigger) if hasattr(job, 'trigger') else '',
                'next_run_time': job.next_run_time.isoformat() if hasattr(job, 'next_run_time') and job.next_run_time else None,
                'last_run_time': None,  # APScheduler 3.x 不直接存储 last_run_time
            }

if __name__ == "__main__":
    # 示例用法
    def sample_task():
        print("定时任务执行中...")
    
    with TaskScheduler() as scheduler:
        # 添加每分钟执行一次的任务
        job_id = scheduler.add_cron_job(sample_task, "* * * * * *")
        print(f"已添加任务: {job_id}")
        input("按Enter键退出...\n")
    pass