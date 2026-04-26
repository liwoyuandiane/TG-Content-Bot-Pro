"""
智能重试处理工具
提供灵活的重试机制，支持指数退避、自定义重试条件和错误分类
"""
import asyncio
import functools
import logging
import random
from typing import Callable, Any, Optional, Union, List, Type
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RetryStrategy:
    """重试策略配置"""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_on_exceptions: Optional[List[Type[Exception]]] = None
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_on_exceptions = retry_on_exceptions or [Exception]
    
    def get_delay(self, attempt: int) -> float:
        """计算重试延迟时间"""
        delay = min(
            self.initial_delay * (self.exponential_base ** (attempt - 1)),
            self.max_delay
        )
        
        if self.jitter:
            # 添加随机抖动，避免重试风暴
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay


def retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_on_exceptions: Optional[List[Type[Exception]]] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        initial_delay: 初始延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        exponential_base: 指数退避基数
        jitter: 是否添加随机抖动
        retry_on_exceptions: 重试的异常类型列表
        on_retry: 重试回调函数
    """
    strategy = RetryStrategy(
        max_retries=max_retries,
        initial_delay=initial_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        retry_on_exceptions=retry_on_exceptions
    )
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(strategy.max_retries + 1):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                
                except Exception as e:
                    last_exception = e
                    
                    # 检查是否是需要重试的异常
                    if not any(isinstance(e, exc_type) for exc_type in strategy.retry_on_exceptions):
                        logger.debug(f"异常 {type(e).__name__} 不在重试范围内，直接抛出")
                        raise
                    
                    # 检查是否达到最大重试次数
                    if attempt == strategy.max_retries:
                        logger.warning(f"函数 {func.__name__} 重试 {attempt} 次后失败: {e}")
                        raise
                    
                    # 计算延迟时间
                    delay = strategy.get_delay(attempt + 1)
                    
                    # 记录重试信息
                    logger.info(
                        f"函数 {func.__name__} 第 {attempt + 1} 次重试，等待 {delay:.2f} 秒后重试: {e}"
                    )
                    
                    # 调用重试回调
                    if on_retry:
                        try:
                            on_retry(e, attempt + 1)
                        except Exception as callback_error:
                            logger.error(f"重试回调函数出错: {callback_error}")
                    
                    # 等待延迟时间
                    await asyncio.sleep(delay)
            
            # 这行代码理论上不会执行
            raise last_exception
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(strategy.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                
                except Exception as e:
                    last_exception = e
                    
                    # 检查是否是需要重试的异常
                    if not any(isinstance(e, exc_type) for exc_type in strategy.retry_on_exceptions):
                        logger.debug(f"异常 {type(e).__name__} 不在重试范围内，直接抛出")
                        raise
                    
                    # 检查是否达到最大重试次数
                    if attempt == strategy.max_retries:
                        logger.warning(f"函数 {func.__name__} 重试 {attempt} 次后失败: {e}")
                        raise
                    
                    # 计算延迟时间
                    delay = strategy.get_delay(attempt + 1)
                    
                    # 记录重试信息
                    logger.info(
                        f"函数 {func.__name__} 第 {attempt + 1} 次重试，等待 {delay:.2f} 秒后重试: {e}"
                    )
                    
                    # 调用重试回调
                    if on_retry:
                        try:
                            on_retry(e, attempt + 1)
                        except Exception as callback_error:
                            logger.error(f"重试回调函数出错: {callback_error}")
                    
                    # 等待延迟时间（同步版本）
                    import time
                    time.sleep(delay)
            
            # 这行代码理论上不会执行
            raise last_exception
        
        # 根据函数类型返回相应的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# 预定义的重试策略
class RetryStrategies:
    """预定义的重试策略"""
    
    @staticmethod
    def network_operations():
        """网络操作重试策略"""
        return retry(
            max_retries=5,
            initial_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=True,
            retry_on_exceptions=[ConnectionError, TimeoutError]
        )
    
    @staticmethod
    def database_operations():
        """数据库操作重试策略"""
        return retry(
            max_retries=3,
            initial_delay=2.0,
            max_delay=10.0,
            exponential_base=1.5,
            jitter=True,
            retry_on_exceptions=[ConnectionError]
        )
    
    @staticmethod
    def telegram_api_operations():
        """Telegram API 操作重试策略"""
        return retry(
            max_retries=3,
            initial_delay=3.0,
            max_delay=15.0,
            exponential_base=2.0,
            jitter=True,
            retry_on_exceptions=[ConnectionError, TimeoutError]
        )


def retry_with_backoff(
    func: Callable,
    *args,
    max_retries: int = 3,
    **kwargs
) -> Any:
    """
    带退避策略的重试函数
    
    Args:
        func: 要重试的函数
        max_retries: 最大重试次数
        *args: 函数参数
        **kwargs: 函数关键字参数
    
    Returns:
        函数执行结果
    
    Raises:
        最后一次重试的异常
    """
    strategy = RetryStrategy(max_retries=max_retries)
    
    for attempt in range(strategy.max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return asyncio.run(func(*args, **kwargs))
            else:
                return func(*args, **kwargs)
        
        except Exception as e:
            if attempt == strategy.max_retries:
                logger.error(f"函数 {func.__name__} 重试 {attempt} 次后失败")
                raise
            
            delay = strategy.get_delay(attempt + 1)
            logger.warning(f"函数 {func.__name__} 第 {attempt + 1} 次重试，等待 {delay:.2f} 秒")
            
            if asyncio.iscoroutinefunction(func):
                asyncio.sleep(delay)
            else:
                import time
                time.sleep(delay)


class CircuitBreaker:
    """断路器模式实现"""
    
    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func: Callable, *args, **kwargs):
        """通过断路器调用函数"""
        if self.state == "OPEN":
            # 检查是否应该尝试半开状态
            if (datetime.now() - self.last_failure_time).total_seconds() > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpen(f"断路器已打开，拒绝调用 {func.__name__}")
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # 调用成功，重置断路器
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
            self.failure_count = 0
            
            return result
        
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            
            logger.error(f"断路器状态: {self.state}, 失败次数: {self.failure_count}")
            raise


class CircuitBreakerOpen(Exception):
    """断路器打开异常"""
    pass