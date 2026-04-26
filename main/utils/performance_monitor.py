"""性能监控模块

提供高级性能监控功能，包括实时监控、性能分析和瓶颈识别。
"""
import time
import logging
import threading
import psutil
import asyncio
from typing import Dict, Any, Callable, Optional, List
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class PerformanceRecord:
    """性能记录"""
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    success: bool = True
    error: Optional[str] = None


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, enabled: bool = True):
        """初始化性能监控器
        
        Args:
            enabled: 是否启用性能监控
        """
        self.enabled = enabled
        self._records: Dict[str, PerformanceRecord] = {}
        self._lock = threading.Lock()
        self._threshold_ms = 1000  # 慢操作阈值（毫秒）
        
    @contextmanager
    def measure(self, name: str):
        """测量代码块执行时间的上下文管理器
        
        Args:
            name: 操作名称
            
        Yields:
            PerformanceRecord: 性能记录对象
        """
        if not self.enabled:
            yield None
            return
            
        record = PerformanceRecord(name=name, start_time=time.time())
        
        try:
            yield record
            record.success = True
        except Exception as e:
            record.success = False
            record.error = str(e)
            raise
        finally:
            record.end_time = time.time()
            record.duration = (record.end_time - record.start_time) * 1000  # 转换为毫秒
            
            self._add_record(record)
            
            # 记录慢操作
            if record.duration > self._threshold_ms:
                logger.warning(f"慢操作检测: {name} 耗时 {record.duration:.2f}ms")
    
    def _add_record(self, record: PerformanceRecord):
        """添加性能记录
        
        Args:
            record: 性能记录
        """
        with self._lock:
            key = f"{record.name}_{int(record.start_time * 1000)}"
            self._records[key] = record
            
            # 保持最近1000条记录
            if len(self._records) > 1000:
                # 移除最早的记录
                oldest_key = min(self._records.keys(), key=lambda k: self._records[k].start_time)
                del self._records[oldest_key]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取性能统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        with self._lock:
            if not self._records:
                return {}
            
            records = list(self._records.values())
            durations = [r.duration for r in records if r.duration is not None]
            
            return {
                'total_operations': len(records),
                'success_rate': sum(1 for r in records if r.success) / len(records) * 100,
                'avg_duration_ms': sum(durations) / len(durations) if durations else 0,
                'max_duration_ms': max(durations) if durations else 0,
                'min_duration_ms': min(durations) if durations else 0,
                'slow_operations': sum(1 for d in durations if d > self._threshold_ms),
                'last_operation': max(r.start_time for r in records) if records else 0
            }
    
    def get_top_slow_operations(self, limit: int = 10) -> list:
        """获取最慢的操作
        
        Args:
            limit: 返回数量限制
            
        Returns:
            list: 最慢操作列表
        """
        with self._lock:
            slow_records = [r for r in self._records.values() 
                          if r.duration and r.duration > self._threshold_ms]
            slow_records.sort(key=lambda r: r.duration, reverse=True)
            return slow_records[:limit]
    
    def reset(self):
        """重置性能记录"""
        with self._lock:
            self._records.clear()
    
    def set_threshold(self, threshold_ms: int):
        """设置慢操作阈值
        
        Args:
            threshold_ms: 阈值（毫秒）
        """
        self._threshold_ms = threshold_ms


def performance_decorator(func: Callable) -> Callable:
    """性能监控装饰器
    
    Args:
        func: 被装饰的函数
        
    Returns:
        Callable: 装饰后的函数
    """
    def wrapper(*args, **kwargs):
        monitor = PerformanceMonitor()
        func_name = f"{func.__module__}.{func.__name__}"
        
        with monitor.measure(func_name) as record:
            result = func(*args, **kwargs)
            
        # 如果函数执行时间超过阈值，记录警告
        if record and record.duration and record.duration > monitor._threshold_ms:
            logger.warning(f"函数 {func_name} 执行缓慢: {record.duration:.2f}ms")
            
        return result
    
    return wrapper


# 全局性能监控实例
performance_monitor = PerformanceMonitor()