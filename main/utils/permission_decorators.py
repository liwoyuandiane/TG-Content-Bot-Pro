"""
通用权限装饰器
提供统一的权限检查装饰器，减少代码重复
"""
import functools
import logging
from typing import Callable, Any, Optional
from telethon import events

from ..services.permission_service import permission_service

logger = logging.getLogger(__name__)


def require_permission(permission_level: str, error_message: Optional[str] = None):
    """
    通用权限检查装饰器
    
    Args:
        permission_level: 权限级别 ("owner" 或 "authorized")
        error_message: 自定义错误消息
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(event: events.NewMessage.Event, *args, **kwargs):
            user_id = event.sender_id
            
            # 检查权限
            if permission_level == "owner":
                has_permission = await permission_service.require_owner(user_id)
                if not has_permission:
                    msg = error_message or "❌ 此命令仅限所有者使用"
                    await event.reply(msg)
                    return
            
            elif permission_level == "authorized":
                has_permission = await permission_service.require_authorized(user_id)
                if not has_permission:
                    msg = error_message or "❌ 您没有权限使用此命令"
                    await event.reply(msg)
                    return
            
            else:
                logger.error(f"无效的权限级别: {permission_level}")
                await event.reply("❌ 权限配置错误")
                return
            
            # 执行原始函数
            return await func(event, *args, **kwargs)
        
        return wrapper
    
    return decorator


def require_owner(error_message: Optional[str] = None):
    """要求所有者权限的装饰器"""
    return require_permission("owner", error_message)


def require_authorized(error_message: Optional[str] = None):
    """要求授权用户权限的装饰器"""
    return require_permission("authorized", error_message)


def rate_limit(requests_per_minute: int = 30, error_message: Optional[str] = None):
    """
    速率限制装饰器
    
    Args:
        requests_per_minute: 每分钟最大请求数
        error_message: 自定义错误消息
    """
    import time
    from collections import defaultdict
    
    # 存储用户请求时间戳
    user_requests = defaultdict(list)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(event: events.NewMessage.Event, *args, **kwargs):
            user_id = event.sender_id
            current_time = time.time()
            
            # 清理过期的请求记录
            user_requests[user_id] = [
                timestamp for timestamp in user_requests[user_id]
                if current_time - timestamp < 60  # 只保留最近60秒的记录
            ]
            
            # 检查速率限制
            if len(user_requests[user_id]) >= requests_per_minute:
                msg = error_message or f"❌ 请求过于频繁，请稍后再试（限制: {requests_per_minute}次/分钟）"
                await event.reply(msg)
                return
            
            # 记录当前请求
            user_requests[user_id].append(current_time)
            
            # 执行原始函数
            return await func(event, *args, **kwargs)
        
        return wrapper
    
    return decorator


def log_command_usage(command_name: str):
    """
    命令使用日志装饰器
    
    Args:
        command_name: 命令名称
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(event: events.NewMessage.Event, *args, **kwargs):
            user_id = event.sender_id
            
            logger.info(f"用户 {user_id} 执行命令: {command_name}")
            
            try:
                result = await func(event, *args, **kwargs)
                logger.info(f"命令 {command_name} 执行成功 (用户: {user_id})")
                return result
            except Exception as e:
                logger.error(f"命令 {command_name} 执行失败 (用户: {user_id}): {e}")
                raise
        
        return wrapper
    
    return decorator


def handle_errors(default_return: Any = None, log_errors: bool = True):
    """
    错误处理装饰器
    
    Args:
        default_return: 出错时的默认返回值
        log_errors: 是否记录错误日志
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(event: events.NewMessage.Event, *args, **kwargs):
            try:
                return await func(event, *args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"命令执行出错: {func.__name__}, 错误: {e}", exc_info=True)
                
                # 发送错误消息给用户
                try:
                    await event.reply("❌ 命令执行出错，请稍后重试")
                except Exception:
                    pass  # 忽略发送错误消息时的错误
                
                return default_return
        
        return wrapper
    
    return decorator


def combined_decorator(*decorators):
    """
    组合多个装饰器
    
    Args:
        *decorators: 要组合的装饰器
    """
    def decorator(func: Callable) -> Callable:
        for dec in reversed(decorators):
            func = dec(func)
        return func
    
    return decorator


# 预定义的装饰器组合
class CommandDecorators:
    """预定义的装饰器组合"""
    
    @staticmethod
    def owner_command(command_name: str):
        """所有者命令装饰器组合"""
        return combined_decorator(
            require_owner(),
            log_command_usage(command_name),
            handle_errors()
        )
    
    @staticmethod
    def authorized_command(command_name: str):
        """授权用户命令装饰器组合"""
        return combined_decorator(
            require_authorized(),
            rate_limit(requests_per_minute=60),
            log_command_usage(command_name),
            handle_errors()
        )
    
    @staticmethod
    def public_command(command_name: str):
        """公开命令装饰器组合"""
        return combined_decorator(
            rate_limit(requests_per_minute=30),
            log_command_usage(command_name),
            handle_errors()
        )


# 使用示例
"""
# 在插件中的使用示例

@require_owner()
async def admin_command(event):
    # 只有所有者可以执行的命令
    await event.reply("这是管理员命令")

@require_authorized()
@rate_limit(requests_per_minute=30)
async def user_command(event):
    # 授权用户可以执行的命令，有速率限制
    await event.reply("这是用户命令")

# 使用预定义的装饰器组合
@CommandDecorators.owner_command("admin_stats")
async def admin_stats_command(event):
    # 自动包含所有者权限检查、日志记录和错误处理
    await event.reply("管理员统计信息")
"""