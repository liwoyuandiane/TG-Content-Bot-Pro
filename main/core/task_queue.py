"""任务队列管理模块"""
import asyncio
import logging
import time
import uuid
from typing import Optional, Callable, Any, Dict, List
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from ..utils.error_handler import handle_errors

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    name: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Any = None
    priority: int = 0
    task_func: Optional[Callable] = None
    args: tuple = ()
    kwargs: dict = None
    
    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}


class TaskQueueError(Exception):
    """任务队列异常"""
    pass


class ImprovedTaskQueue:
    """改进的任务队列系统"""
    
    def __init__(self, max_workers: int = 3, queue_max_size: int = 1000):
        self.max_workers = max_workers
        self.queue_max_size = queue_max_size
        
        # 智能并发控制
        self._concurrency_limiter = asyncio.Semaphore(max_workers)
        self._memory_threshold = 0.9  # 内存使用阈值
        self._cpu_threshold = 0.8     # CPU使用阈值
        
        # 自适应控制
        self._adaptive_timer = None
        self._current_concurrency = max_workers
        from ..config import settings
        self._min_concurrency = max(1, int(getattr(settings, 'MIN_CONCURRENCY', 1)))
        self._max_concurrency = max(self._min_concurrency, int(getattr(settings, 'MAX_CONCURRENCY', 10)))
        self._upscale_enable = True  # 允许在低负载时上调并发
        
        # 使用asyncio.Queue替代deque，提供更好的线程安全性
        self.pending_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.running_tasks: Dict[str, TaskInfo] = {}
        self.completed_tasks: Dict[str, TaskInfo] = {}
        self.workers: List[asyncio.Task] = []
        self.is_running = False
        
        # 统计信息
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "cancelled_tasks": 0
        }
        
        # 锁
        self._lock = asyncio.Lock()
        self._stats_lock = asyncio.Lock()
    
    async def start(self):
        """启动任务队列"""
        if self.is_running:
            logger.warning("任务队列已在运行中")
            return
        
        self.is_running = True
        
        # 启动工作线程
        self.workers = [
            asyncio.create_task(self._worker(i), name=f"task_worker_{i}")
            for i in range(self.max_workers)
        ]
        
        # 启动自适应监控
        self._adaptive_timer = asyncio.create_task(self._adaptive_monitor(), name="adaptive_monitor")
        
        logger.info(f"任务队列已启动，工作线程数: {self.max_workers}")
    
    async def stop(self, timeout: float = 5.0):
        """停止任务队列"""
        if not self.is_running:
            return
        
        logger.info("正在停止任务队列...")
        self.is_running = False
        
        # 取消所有工作线程
        for worker in self.workers:
            if not worker.done():
                worker.cancel()
        
        # 等待工作线程完成
        try:
            await asyncio.wait_for(
                asyncio.gather(*self.workers, return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning("等待工作线程停止超时")
        
        logger.info("任务队列已停止")
    
    async def _adaptive_monitor(self):
        """自适应监控和调整"""
        while self.is_running:
            try:
                await asyncio.sleep(30)  # 每30秒检查一次
                
                # 检查系统资源
                memory_usage = await self._get_memory_usage()
                cpu_usage = await self._get_cpu_usage()
                
                # 根据资源使用情况调整并发数
                await self._adjust_concurrency(memory_usage, cpu_usage)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"自适应监控错误: {e}")
    
    async def _get_memory_usage(self) -> float:
        """获取内存使用率"""
        try:
            import psutil
            return psutil.virtual_memory().percent / 100.0
        except ImportError:
            # 如果没有psutil，返回默认值
            return 0.5
        except Exception as e:
            logger.error(f"获取内存使用率失败: {e}")
            return 0.5
    
    async def _get_cpu_usage(self) -> float:
        """获取CPU使用率"""
        try:
            import psutil
            return psutil.cpu_percent(interval=1) / 100.0
        except ImportError:
            # 如果没有psutil，返回默认值
            return 0.3
        except Exception as e:
            logger.error(f"获取CPU使用率失败: {e}")
            return 0.3
    
    async def _adjust_concurrency(self, memory_usage: float, cpu_usage: float):
        """根据资源使用情况调整并发数"""
        old_concurrency = self._current_concurrency

        # 当前队列与运行任务情况
        pending_size = self.pending_queue.qsize()
        running_count = len(self.running_tasks)
        
        # 如果资源使用过高，减少并发（与任务数量无关）
        if memory_usage > self._memory_threshold or cpu_usage > self._cpu_threshold:
            new_concurrency = max(self._min_concurrency, self._current_concurrency - 1)
        # 仅当存在待处理或运行中的任务，且负载较低时才上调并发
        elif (pending_size > 0 or running_count > 0) and self._upscale_enable and \
             memory_usage < self._memory_threshold * 0.7 and cpu_usage < self._cpu_threshold * 0.7:
            new_concurrency = min(self._max_concurrency, self._current_concurrency + 1)
        else:
            # 保持当前并发
            return
        
        if new_concurrency != old_concurrency:
            await self._update_concurrency(new_concurrency)
            logger.info(
                f"并发数已从 {old_concurrency} 调整为 {new_concurrency} "
                f"(内存: {memory_usage:.1%}, CPU: {cpu_usage:.1%}, pending: {pending_size}, running: {running_count})"
            )
    
    async def _update_concurrency(self, new_concurrency: int):
        """更新并发限制"""
        self._current_concurrency = new_concurrency
        # 创建新的信号量
        self._concurrency_limiter = asyncio.Semaphore(new_concurrency)
    
    async def _worker(self, worker_id: int):
        """工作线程"""
        logger.info(f"工作线程 {worker_id} 已启动")
        
        while self.is_running:
            try:
                # 从队列获取任务
                priority, task_info = await self.pending_queue.get()
                
                # 检查任务是否已被取消
                async with self._lock:
                    if task_info.task_id not in self.running_tasks:
                        self.pending_queue.task_done()
                        continue
                
                logger.info(f"工作线程 {worker_id} 正在处理任务 {task_info.name} ({task_info.task_id})")
                
                # 更新任务状态为运行中
                async with self._lock:
                    task_info.status = TaskStatus.RUNNING
                    task_info.started_at = datetime.now()
                    self.running_tasks[task_info.task_id] = task_info
                
                # 执行任务
                try:
                    # 这里需要从某个地方获取实际的任务函数和参数
                    # 由于重构，我们需要重新设计任务执行方式
                    result = await self._execute_task(task_info)
                    
                    # 更新任务状态为完成
                    async with self._lock:
                        task_info.status = TaskStatus.COMPLETED
                        task_info.completed_at = datetime.now()
                        task_info.result = result
                        self.completed_tasks[task_info.task_id] = task_info
                        del self.running_tasks[task_info.task_id]
                    
                    async with self._stats_lock:
                        self.stats["completed_tasks"] += 1
                        self.stats["total_tasks"] += 1
                    
                    logger.info(f"任务 {task_info.name} ({task_info.task_id}) 执行成功")
                    
                except Exception as e:
                    logger.error(f"任务 {task_info.name} ({task_info.task_id}) 执行失败: {e}", exc_info=True)
                    
                    # 更新任务状态为失败
                    async with self._lock:
                        task_info.status = TaskStatus.FAILED
                        task_info.completed_at = datetime.now()
                        task_info.error = str(e)
                        self.completed_tasks[task_info.task_id] = task_info
                        del self.running_tasks[task_info.task_id]
                    
                    async with self._stats_lock:
                        self.stats["failed_tasks"] += 1
                        self.stats["total_tasks"] += 1
                
                finally:
                    self.pending_queue.task_done()
                    
            except asyncio.CancelledError:
                logger.info(f"工作线程 {worker_id} 被取消")
                break
            except Exception as e:
                logger.error(f"工作线程 {worker_id} 发生错误: {e}", exc_info=True)
                await asyncio.sleep(1)
        
        logger.info(f"工作线程 {worker_id} 已停止")
    
    async def _execute_task(self, task_info: TaskInfo) -> Any:
        """执行任务"""
        if task_info.task_func is None:
            raise NotImplementedError("任务函数未定义")
        
        # 执行任务函数
        if asyncio.iscoroutinefunction(task_info.task_func):
            return await task_info.task_func(*task_info.args, **task_info.kwargs)
        else:
            return task_info.task_func(*task_info.args, **task_info.kwargs)
    
    def add_task(self, name: str, task_func: Callable, *args, priority: int = 0, **kwargs) -> str:
        """添加任务到队列"""
        if not self.is_running:
            raise TaskQueueError("任务队列未运行")
        
        if self.pending_queue.qsize() >= self.queue_max_size:
            raise TaskQueueError(f"任务队列已满 (最大容量: {self.queue_max_size})")
        
        task_id = str(uuid.uuid4())
        task_info = TaskInfo(
            task_id=task_id,
            name=name,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            priority=priority
        )
        
        # 存储任务函数和参数到task_info中
        task_info.task_func = task_func
        task_info.args = args
        task_info.kwargs = kwargs
        
        # 注意：Python的PriorityQueue是小顶堆，所以我们使用负数来实现大顶堆
        self.pending_queue.put_nowait((-priority, task_info))
        
        # 添加到运行中任务列表
        self.running_tasks[task_id] = task_info
        
        logger.info(f"任务 {name} ({task_id}) 已加入队列，优先级: {priority}")
        return task_id
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        async with self._lock:
            # 检查运行中的任务
            if task_id in self.running_tasks:
                return asdict(self.running_tasks[task_id])
            
            # 检查已完成的任务
            if task_id in self.completed_tasks:
                return asdict(self.completed_tasks[task_id])
            
            return None
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        async with self._lock:
            async with self._stats_lock:
                return {
                    "pending_tasks": self.pending_queue.qsize(),
                    "running_tasks": len(self.running_tasks),
                    "completed_tasks": len(self.completed_tasks),
                    "workers": len(self.workers),
                    "stats": self.stats.copy()
                }
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        async with self._lock:
            # 检查是否在运行中任务列表中
            if task_id in self.running_tasks:
                task_info = self.running_tasks[task_id]
                task_info.status = TaskStatus.CANCELLED
                task_info.completed_at = datetime.now()
                self.completed_tasks[task_id] = task_info
                del self.running_tasks[task_id]
                
                async with self._stats_lock:
                    self.stats["cancelled_tasks"] += 1
                    self.stats["total_tasks"] += 1
                
                logger.info(f"任务 {task_info.name} ({task_id}) 已取消")
                return True
            
            # 检查是否在等待队列中
            # 注意：对于PriorityQueue，我们无法直接移除元素
            # 这里可以标记任务为已取消，但在_worker中需要检查
            
            return False
    
    async def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """等待任务完成"""
        start_time = time.time()
        
        while True:
            status = await self.get_task_status(task_id)
            if not status:
                return None
            
            if status["status"] in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]:
                return status
            
            if timeout and (time.time() - start_time) >= timeout:
                return None
            
            await asyncio.sleep(0.1)
    
    async def clear_completed_tasks(self, older_than: Optional[float] = None):
        """清理已完成的任务"""
        async with self._lock:
            if older_than is None:
                count = len(self.completed_tasks)
                self.completed_tasks.clear()
                logger.info(f"已清理 {count} 个已完成的任务")
            else:
                now = datetime.now()
                to_remove = []
                for task_id, task_info in self.completed_tasks.items():
                    if (now - task_info.completed_at).total_seconds() > older_than:
                        to_remove.append(task_id)
                
                for task_id in to_remove:
                    del self.completed_tasks[task_id]
                
                logger.info(f"已清理 {len(to_remove)} 个过期的已完成任务")


# 全局任务队列实例
task_queue = ImprovedTaskQueue(max_workers=2)


async def get_task_queue() -> ImprovedTaskQueue:
    """获取任务队列实例的便捷函数"""
    return task_queue