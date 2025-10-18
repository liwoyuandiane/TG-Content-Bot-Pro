"""错误处理工具模块"""
import logging
import functools
import asyncio
from typing import Callable, Any, Optional
from ..exceptions.base import BaseBotException

logger = logging.getLogger(__name__)


def handle_errors(default_return: Any = None, log_level: int = logging.ERROR):
    """错误处理装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except BaseBotException as e:
                logger.log(log_level, f"业务异常 in {func.__name__}: {e}")
                return default_return
            except Exception as e:
                logger.log(log_level, f"未处理异常 in {func.__name__}: {e}", exc_info=True)
                return default_return
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except BaseBotException as e:
                logger.log(log_level, f"业务异常 in {func.__name__}: {e}")
                return default_return
            except Exception as e:
                logger.log(log_level, f"未处理异常 in {func.__name__}: {e}", exc_info=True)
                return default_return
        
        # 根据函数是否为异步函数返回相应的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def safe_execute(func: Callable, *args, default_return: Any = None, **kwargs) -> Any:
    """安全执行函数"""
    try:
        return func(*args, **kwargs)
    except BaseBotException as e:
        logger.error(f"业务异常 in {func.__name__}: {e}")
        return default_return
    except Exception as e:
        logger.error(f"未处理异常 in {func.__name__}: {e}", exc_info=True)
        return default_return


async def safe_execute_async(func: Callable, *args, default_return: Any = None, **kwargs) -> Any:
    """安全异步执行函数"""
    try:
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    except BaseBotException as e:
        logger.error(f"业务异常 in {func.__name__}: {e}")
        return default_return
    except Exception as e:
        logger.error(f"未处理异常 in {func.__name__}: {e}", exc_info=True)
        return default_return