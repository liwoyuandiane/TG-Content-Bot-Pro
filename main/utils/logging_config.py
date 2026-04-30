"""日志配置模块

提供高级日志配置功能，包括日志轮转、结构化日志和性能优化。
"""
import logging
import os
import sys
import json
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Dict, Any, Optional

from ..config import settings


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        super().__init__(fmt, datefmt)
        self.enable_json = settings.ENVIRONMENT == "production"
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录
        
        Args:
            record: 日志记录
            
        Returns:
            格式化后的日志字符串
        """
        if self.enable_json:
            # 生产环境使用JSON格式
            log_data = {
                "timestamp": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno
            }
            
            # 添加额外字段
            if hasattr(record, 'user_id') and record.user_id:
                log_data["user_id"] = record.user_id
            
            if hasattr(record, 'chat_id') and record.chat_id:
                log_data["chat_id"] = record.chat_id
            
            if hasattr(record, 'message_id') and record.message_id:
                log_data["message_id"] = record.message_id
            
            if record.exc_info:
                log_data["exception"] = self.formatException(record.exc_info)
            
            return json.dumps(log_data, ensure_ascii=False)
        else:
            # 开发环境使用易读格式
            return super().format(record)


def setup_logging():
    """设置日志配置 - 支持日志轮转和结构化日志"""
    # 强制开发环境配置
    env = os.getenv('ENVIRONMENT', 'development')
    debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
    
    # 开发环境强制使用详细日志
    if env == 'development' or debug_mode:
        log_level = logging.DEBUG
        log_level_name = 'DEBUG'
    else:
        log_level_name = settings.LOG_LEVEL.upper()
        log_level = getattr(logging, log_level_name, logging.INFO)
    
    # 清除现有的处理器
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 创建日志目录
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # 清理旧的日志文件，只保留最新的10个
    _cleanup_old_logs(log_dir)
    
    # 定义日志格式
    log_formats = {
        'console': '[%(asctime)s] [%(levelname)8s] [%(name)20s:%(lineno)4d] %(message)s',
        'file': '[%(asctime)s] [%(levelname)s] [%(name)s] [%(module)s.%(funcName)s:%(lineno)d] %(message)s',
        'datefmt': '%Y-%m-%d %H:%M:%S'
    }
    
    # 创建格式化器
    console_formatter = logging.Formatter(log_formats['console'], log_formats['datefmt'])
    file_formatter = StructuredFormatter(log_formats['file'], log_formats['datefmt'])
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # 添加文件处理器（固定文件名 tg_bot.log）
    log_file = _get_log_file(log_dir)
    
    # 检查日志文件大小，超过5MB则清空
    if os.path.exists(log_file) and os.path.getsize(log_file) > 5 * 1024 * 1024:
        with open(log_file, 'w') as f:
            f.truncate(0)
        print(f"📄 日志文件已清空（超过5MB）")
    
    # 使用 AutoReopenFileHandler 支持日志文件被删除后自动重新创建
    file_handler = AutoReopenFileHandler(
        filename=log_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=0,              # 不保留备份（达到上限直接清空）
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # 设置根日志级别
    root_logger.setLevel(log_level)
    
    # 优化第三方库日志级别
    _optimize_third_party_logging()
    
    # 开发环境额外配置
    if env == 'development' or debug_mode:
        # 启用所有模块的DEBUG级别
        logging.getLogger('main').setLevel(logging.DEBUG)
        logging.getLogger('utils').setLevel(logging.DEBUG)
        logging.getLogger('core').setLevel(logging.DEBUG)
        logging.getLogger('services').setLevel(logging.DEBUG)
        
        print("=" * 70)
        print("🔧 开发模式日志系统已初始化")
        print(f"📊 日志级别: {log_level_name}")
        print(f"🌍 环境: {env}")
        print(f"🐛 调试模式: {debug_mode}")
        print(f"📁 日志文件: {os.path.abspath(log_file)}")
        print("=" * 70)
    
    return logging.getLogger(__name__)


def _get_log_file(log_dir: str) -> str:
    """获取日志文件名（固定为 tg_bot.log）"""
    return os.path.join(log_dir, "tg_bot.log")


class AutoReopenFileHandler(RotatingFileHandler):
    """自动重新打开文件的 Handler，用于处理日志文件被删除的情况"""
    def emit(self, record):
        try:
            if self.stream is None or not os.path.exists(self.baseFilename):
                self.reopen()
            super().emit(record)
        except Exception:
            self.handleError(record)
    
    def reopen(self):
        """重新打开日志文件"""
        if self.stream:
            try:
                self.stream.close()
            except:
                pass
        self.stream = open(self.baseFilename, self.mode)


def _cleanup_old_logs(log_dir: str):
    """清理旧的日志文件（单个文件，不需要清理）"""
    pass


def _optimize_third_party_logging():
    """优化第三方库的日志级别"""
    # 减少第三方库的日志噪音
    noisy_modules = [
        ("pyrogram", logging.WARNING),
        ("pymongo", logging.WARNING),
        ("urllib3", logging.WARNING),
        ("httpx", logging.WARNING),
        ("asyncio", logging.WARNING),
        ("aiohttp", logging.WARNING)
    ]
    
    for module_name, level in noisy_modules:
        logging.getLogger(module_name).setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """获取命名日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        日志记录器实例
    """
    logger = logging.getLogger(name)
    
    # 为特定模块设置优化级别
    if name.startswith("main.services"):
        logger.setLevel(logging.INFO)
    elif name.startswith("main.core"):
        logger.setLevel(logging.INFO)
    
    return logger


def log_with_context(logger: logging.Logger, level: int, message: str, 
                    user_id: Optional[int] = None,
                    chat_id: Optional[int] = None,
                    message_id: Optional[int] = None,
                    **kwargs) -> None:
    """带上下文的日志记录
    
    Args:
        logger: 日志记录器
        level: 日志级别
        message: 日志消息
        user_id: 用户ID
        chat_id: 聊天ID
        message_id: 消息ID
        **kwargs: 额外上下文
    """
    # 创建日志记录
    if logger.isEnabledFor(level):
        record = logger.makeRecord(
            logger.name, level, "", 0, message, (), None,
            func=kwargs.get('func'), extra=kwargs
        )
        
        # 添加上下文信息
        if user_id:
            record.user_id = user_id
        if chat_id:
            record.chat_id = chat_id
        if message_id:
            record.message_id = message_id
        
        logger.handle(record)


class PerformanceLogger:
    """性能日志记录器"""
    
    def __init__(self, logger: logging.Logger):
        """初始化性能日志记录器
        
        Args:
            logger: 基础日志记录器
        """
        self.logger = logger
        self.performance_threshold_ms = 1000  # 性能阈值（毫秒）
    
    def log_performance(self, operation: str, duration_ms: float, 
                       success: bool = True, 
                       user_id: Optional[int] = None,
                       details: Optional[Dict[str, Any]] = None) -> None:
        """记录性能日志
        
        Args:
            operation: 操作名称
            duration_ms: 耗时（毫秒）
            success: 是否成功
            user_id: 用户ID
            details: 详细信息
        """
        level = logging.INFO if success else logging.ERROR
        
        # 构建性能消息
        status = "✅" if success else "❌"
        message = f"{status} {operation} - 耗时: {duration_ms:.2f}ms"
        
        if details:
            message += f" | 详情: {json.dumps(details, ensure_ascii=False)}"
        
        # 记录日志
        log_with_context(self.logger, level, message, user_id=user_id)
        
        # 记录慢操作警告
        if duration_ms > self.performance_threshold_ms:
            self.logger.warning("🐌 慢操作检测: %s 耗时 %.2fms", operation, duration_ms)
    
    def set_threshold(self, threshold_ms: float) -> None:
        """设置性能阈值
        
        Args:
            threshold_ms: 阈值（毫秒）
        """
        self.performance_threshold_ms = threshold_ms


# 创建全局性能日志记录器
performance_logger = PerformanceLogger(get_logger(__name__))