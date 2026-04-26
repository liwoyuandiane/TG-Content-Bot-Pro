"""错误处理模块

提供统一的错误处理机制，包括异常捕获、日志记录和错误恢复。
"""
import logging
import traceback
import asyncio
from typing import Any, Callable, Optional, Dict, Type
from functools import wraps
from datetime import datetime, timedelta

from ..config import settings

logger = logging.getLogger(__name__)


class ErrorHandler:
    """错误处理器类"""
    
    def __init__(self):
        """初始化错误处理器"""
        self.error_stats: Dict[str, Dict[str, Any]] = {}
        self.last_error_time: Optional[datetime] = None
        self.error_threshold = 10  # 错误阈值
        self.error_window = timedelta(minutes=5)  # 错误窗口时间
    
    def handle_error(self, error: Exception, context: str = "", 
                    user_id: Optional[int] = None, 
                    should_retry: bool = False) -> bool:
        """处理错误
        
        Args:
            error: 异常对象
            context: 错误上下文描述
            user_id: 相关用户ID（可选）
            should_retry: 是否应该重试
            
        Returns:
            True表示错误已处理，False表示达到错误阈值
        """
        error_type = type(error).__name__
        error_msg = str(error)
        
        # 记录错误统计
        self._record_error_stat(error_type, context, user_id)
        
        # 检查错误频率
        if self._check_error_threshold():
            logger.critical("错误频率过高，达到阈值限制")
            return False
        
        # 记录错误日志
        self._log_error(error, context, user_id)
        
        # 根据错误类型采取不同处理策略
        return self._apply_error_strategy(error, should_retry)
    
    def _record_error_stat(self, error_type: str, context: str, user_id: Optional[int]) -> None:
        """记录错误统计"""
        now = datetime.now()
        
        if error_type not in self.error_stats:
            self.error_stats[error_type] = {
                'count': 0,
                'first_occurrence': now,
                'last_occurrence': now,
                'contexts': set(),
                'user_ids': set()
            }
        
        stat = self.error_stats[error_type]
        stat['count'] += 1
        stat['last_occurrence'] = now
        stat['contexts'].add(context)
        
        if user_id:
            stat['user_ids'].add(user_id)
        
        self.last_error_time = now
    
    def _check_error_threshold(self) -> bool:
        """检查错误阈值"""
        if not self.last_error_time:
            return False
        
        # 检查最近错误频率
        recent_errors = 0
        cutoff_time = datetime.now() - self.error_window
        
        for stat in self.error_stats.values():
            if stat['last_occurrence'] > cutoff_time:
                recent_errors += stat['count']
        
        return recent_errors >= self.error_threshold
    
    def _log_error(self, error: Exception, context: str, user_id: Optional[int]) -> None:
        """记录错误日志"""
        error_type = type(error).__name__
        
        # 构建日志消息
        log_parts = [f"错误类型: {error_type}"]
        
        if context:
            log_parts.append(f"上下文: {context}")
        
        if user_id:
            log_parts.append(f"用户ID: {user_id}")
        
        log_parts.append(f"错误信息: {str(error)}")
        
        # 根据错误类型选择日志级别
        if isinstance(error, (ConnectionError, TimeoutError)):
            logger.warning(" | ".join(log_parts))
        elif isinstance(error, (ValueError, TypeError)):
            logger.error(" | ".join(log_parts))
        else:
            logger.error(" | ".join(log_parts))
            
        # 在调试模式下记录完整堆栈跟踪
        if settings.DEBUG:
            logger.debug("完整堆栈跟踪:\n%s", traceback.format_exc())
    
    def _apply_error_strategy(self, error: Exception, should_retry: bool) -> bool:
        """应用错误处理策略"""
        error_type = type(error)
        
        # 网络相关错误 - 建议重试
        if error_type in [ConnectionError, TimeoutError, asyncio.TimeoutError]:
            logger.warning("网络错误，建议检查网络连接")
            return should_retry
        
        # 认证相关错误 - 需要用户干预
        elif error_type in [PermissionError, ValueError] and "auth" in str(error).lower():
            logger.error("认证错误，需要检查配置")
            return False
        
        # 配置相关错误 - 需要修复配置
        elif "config" in str(error).lower() or "setting" in str(error).lower():
            logger.error("配置错误，需要修复配置文件")
            return False
        
        # 其他错误 - 根据情况决定
        else:
            logger.error("未知错误类型，建议检查日志")
            return should_retry
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计信息
        
        Returns:
            错误统计字典
        """
        total_errors = sum(stat['count'] for stat in self.error_stats.values())
        
        return {
            'total_errors': total_errors,
            'error_types': len(self.error_stats),
            'error_details': self.error_stats,
            'last_error_time': self.last_error_time,
            'error_threshold': self.error_threshold,
            'error_window_minutes': self.error_window.total_seconds() / 60
        }
    
    def reset_statistics(self) -> None:
        """重置错误统计"""
        self.error_stats.clear()
        self.last_error_time = None


def retry_on_error(max_retries: int = 3, delay: float = 1.0, 
                  backoff_factor: float = 2.0,
                  exceptions: tuple = (Exception,)):
    """错误重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff_factor: 退避因子
        exceptions: 需要重试的异常类型
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                last_exception = None
                current_delay = delay
                
                for attempt in range(max_retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        
                        if attempt == max_retries:
                            logger.error("达到最大重试次数 (%d)，放弃重试", max_retries)
                            raise
                        
                        logger.warning("操作失败，%d秒后重试 (尝试 %d/%d)", 
                                     current_delay, attempt + 1, max_retries)
                        
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff_factor
                
                raise last_exception
            
            return async_wrapper
        
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                last_exception = None
                current_delay = delay
                
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        
                        if attempt == max_retries:
                            logger.error("达到最大重试次数 (%d)，放弃重试", max_retries)
                            raise
                        
                        logger.warning("操作失败，%d秒后重试 (尝试 %d/%d)", 
                                     current_delay, attempt + 1, max_retries)
                        
                        import time
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                
                raise last_exception
            
            return sync_wrapper
    
    return decorator


def safe_execute(default_return: Any = None, 
                log_error: bool = True,
                exceptions: tuple = (Exception,)):
    """安全执行装饰器
    
    Args:
        default_return: 出错时的默认返回值
        log_error: 是否记录错误日志
        exceptions: 需要捕获的异常类型
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if log_error:
                        logger.error("安全执行失败: %s", e, exc_info=settings.DEBUG)
                    return default_return
            
            return async_wrapper
        
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if log_error:
                        logger.error("安全执行失败: %s", e, exc_info=settings.DEBUG)
                    return default_return
            
            return sync_wrapper
    
    return decorator


class CircuitBreaker:
    """断路器模式实现"""
    
    def __init__(self, failure_threshold: int = 5, 
                 recovery_timeout: int = 60):
        """初始化断路器
        
        Args:
            failure_threshold: 失败阈值
            recovery_timeout: 恢复超时时间（秒）
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def can_execute(self) -> bool:
        """检查是否允许执行
        
        Returns:
            True表示允许执行，False表示断路器打开
        """
        if self.state == "closed":
            return True
        
        elif self.state == "open":
            # 检查是否超过恢复时间
            if (self.last_failure_time and 
                (datetime.now() - self.last_failure_time).total_seconds() > self.recovery_timeout):
                self.state = "half-open"
                return True
            return False
        
        else:  # half-open
            return True
    
    def record_success(self) -> None:
        """记录成功执行"""
        if self.state == "half-open":
            self.state = "closed"
            self.failure_count = 0
            self.last_failure_time = None
    
    def record_failure(self) -> None:
        """记录失败执行"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning("断路器打开，服务暂时不可用")
    
    def get_state(self) -> str:
        """获取当前状态"""
        return self.state


def handle_errors(error: Exception, context: str = "", user_id: Optional[int] = None) -> bool:
    """处理错误的快捷函数
    
    Args:
        error: 异常对象
        context: 错误上下文描述
        user_id: 相关用户ID（可选）
        
    Returns:
        True表示错误已处理，False表示达到错误阈值
    """
    return error_handler.handle_error(error, context, user_id)


# 创建全局错误处理器实例
error_handler = ErrorHandler()

# 创建常用断路器实例
download_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
api_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)