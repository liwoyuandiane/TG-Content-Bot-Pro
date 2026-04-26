"""
资源管理和内存优化工具
提供内存监控、资源清理和垃圾回收优化功能
"""
import gc
import psutil
import asyncio
import logging
import weakref
from typing import Dict, List, Any, Callable, Optional
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ResourceManager:
    """资源管理器"""
    
    def __init__(self, memory_threshold: float = 0.85, gc_threshold: int = 100):
        self.memory_threshold = memory_threshold
        self.gc_threshold = gc_threshold
        self._tracked_resources: Dict[str, Any] = {}
        self._cleanup_handlers: Dict[str, Callable] = {}
        self._last_cleanup = datetime.now()
        self._cleanup_interval = timedelta(minutes=5)
        self._monitor_task: Optional[asyncio.Task] = None
        self._is_monitoring = False
    
    async def start_monitoring(self):
        """开始资源监控"""
        if self._is_monitoring:
            return
        
        self._is_monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(), name="resource_monitor")
        logger.info("资源监控已启动")
    
    async def stop_monitoring(self):
        """停止资源监控"""
        if not self._is_monitoring:
            return
        
        self._is_monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("资源监控已停止")
    
    async def _monitor_loop(self):
        """监控循环"""
        while self._is_monitoring:
            try:
                await self._check_memory_usage()
                await self._perform_cleanup()
                await asyncio.sleep(60)  # 每分钟检查一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"资源监控出错: {e}")
                await asyncio.sleep(30)
    
    async def _check_memory_usage(self):
        """检查内存使用情况"""
        try:
            memory_percent = psutil.virtual_memory().percent / 100.0
            
            if memory_percent > self.memory_threshold:
                logger.warning(f"内存使用率过高: {memory_percent:.1%}，触发清理")
                await self._force_cleanup()
            
            # 记录内存使用情况（每分钟记录一次）
            if datetime.now().minute % 1 == 0:  # 每分钟记录一次
                logger.debug(f"当前内存使用率: {memory_percent:.1%}")
                
        except Exception as e:
            logger.error(f"检查内存使用情况出错: {e}")
    
    async def _perform_cleanup(self):
        """执行定期清理"""
        now = datetime.now()
        if now - self._last_cleanup >= self._cleanup_interval:
            await self._cleanup_resources()
            self._last_cleanup = now
    
    async def _force_cleanup(self):
        """强制清理资源"""
        logger.info("执行强制资源清理")
        
        # 清理未引用的资源
        await self._cleanup_resources()
        
        # 强制执行垃圾回收
        gc.collect()
        
        # 清理asyncio事件循环
        await self._cleanup_event_loop()
    
    async def _cleanup_resources(self):
        """清理已注册的资源"""
        removed_count = 0
        
        for resource_id, resource in list(self._tracked_resources.items()):
            # 检查资源是否仍然有效
            if not self._is_resource_alive(resource):
                # 执行清理处理程序
                if resource_id in self._cleanup_handlers:
                    try:
                        handler = self._cleanup_handlers[resource_id]
                        if asyncio.iscoroutinefunction(handler):
                            await handler(resource)
                        else:
                            handler(resource)
                    except Exception as e:
                        logger.error(f"清理资源 {resource_id} 时出错: {e}")
                
                # 移除资源
                del self._tracked_resources[resource_id]
                if resource_id in self._cleanup_handlers:
                    del self._cleanup_handlers[resource_id]
                
                removed_count += 1
        
        if removed_count > 0:
            logger.info(f"清理了 {removed_count} 个无效资源")
    
    async def _cleanup_event_loop(self):
        """清理asyncio事件循环"""
        try:
            # 获取当前事件循环
            loop = asyncio.get_event_loop()
            
            # 清理已完成的任务
            completed_tasks = [task for task in asyncio.all_tasks(loop) if task.done()]
            for task in completed_tasks:
                if not task.cancelled():
                    try:
                        task.result()  # 获取结果以清除异常
                    except Exception:
                        pass  # 忽略已完成任务的异常
            
            logger.debug(f"清理了 {len(completed_tasks)} 个已完成任务")
            
        except Exception as e:
            logger.error(f"清理事件循环出错: {e}")
    
    def _is_resource_alive(self, resource: Any) -> bool:
        """检查资源是否仍然有效"""
        try:
            # 对于弱引用，检查是否仍然指向有效对象
            if isinstance(resource, weakref.ReferenceType):
                return resource() is not None
            
            # 对于其他对象，尝试访问简单属性
            if hasattr(resource, '__class__'):
                return True
            
            return False
        except Exception:
            return False
    
    def track_resource(self, resource_id: str, resource: Any, cleanup_handler: Optional[Callable] = None):
        """跟踪资源"""
        # 使用弱引用避免内存泄漏
        weak_resource = weakref.ref(resource)
        self._tracked_resources[resource_id] = weak_resource
        
        if cleanup_handler:
            self._cleanup_handlers[resource_id] = cleanup_handler
        
        logger.debug(f"开始跟踪资源: {resource_id}")
    
    def untrack_resource(self, resource_id: str):
        """停止跟踪资源"""
        if resource_id in self._tracked_resources:
            del self._tracked_resources[resource_id]
        if resource_id in self._cleanup_handlers:
            del self._cleanup_handlers[resource_id]
        
        logger.debug(f"停止跟踪资源: {resource_id}")
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """获取资源统计信息"""
        alive_count = sum(1 for resource in self._tracked_resources.values() 
                         if self._is_resource_alive(resource))
        
        return {
            "total_tracked": len(self._tracked_resources),
            "alive_resources": alive_count,
            "cleanup_handlers": len(self._cleanup_handlers),
            "last_cleanup": self._last_cleanup,
            "is_monitoring": self._is_monitoring
        }


class MemoryOptimizer:
    """内存优化器"""
    
    @staticmethod
    def optimize_gc_settings():
        """优化垃圾回收设置"""
        # 调整GC阈值
        gc.set_threshold(700, 10, 10)
        
        # 启用分代垃圾回收
        if hasattr(gc, 'enable'):
            gc.enable()
        
        logger.info("垃圾回收设置已优化")
    
    @staticmethod
    def get_memory_info() -> Dict[str, Any]:
        """获取内存信息"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                "rss": memory_info.rss,  # 驻留集大小
                "vms": memory_info.vms,  # 虚拟内存大小
                "percent": process.memory_percent(),
                "gc_objects": len(gc.get_objects()),
                "gc_threshold": gc.get_threshold(),
                "gc_count": gc.get_count()
            }
        except Exception as e:
            logger.error(f"获取内存信息出错: {e}")
            return {}
    
    @staticmethod
    def suggest_optimizations() -> List[str]:
        """建议内存优化措施"""
        suggestions = []
        
        try:
            memory_info = MemoryOptimizer.get_memory_info()
            
            if memory_info.get("percent", 0) > 80:
                suggestions.append("内存使用率过高，建议清理缓存数据")
            
            if memory_info.get("gc_objects", 0) > 10000:
                suggestions.append("GC对象过多，建议手动触发垃圾回收")
            
            if memory_info.get("rss", 0) > 500 * 1024 * 1024:  # 500MB
                suggestions.append("内存占用较大，建议检查内存泄漏")
            
        except Exception as e:
            logger.error(f"生成优化建议出错: {e}")
        
        return suggestions


# 全局资源管理器实例
resource_manager = ResourceManager()


def setup_resource_management():
    """设置资源管理"""
    # 优化GC设置
    MemoryOptimizer.optimize_gc_settings()
    
    # 启动资源监控
    asyncio.create_task(resource_manager.start_monitoring())
    
    logger.info("资源管理系统已初始化")


async def cleanup_on_shutdown():
    """应用关闭时的清理操作"""
    logger.info("正在执行关闭清理...")
    
    # 停止资源监控
    await resource_manager.stop_monitoring()
    
    # 执行最终清理
    await resource_manager._force_cleanup()
    
    # 强制执行完整的垃圾回收
    gc.collect()
    
    logger.info("关闭清理完成")