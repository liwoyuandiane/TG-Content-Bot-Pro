"""日志配置模块"""
import logging
import os
from ..config import settings


def setup_logging():
    """设置日志配置 - 每次启动覆盖日志文件"""
    # 创建日志目录
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 日志文件路径
    log_file = os.path.join(log_dir, "bot.log")
    
    # 如果日志文件存在，删除旧文件（覆盖模式）
    if os.path.exists(log_file):
        os.remove(log_file)
    
    # 配置根日志记录器
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    
    # 清除现有的处理器
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 日志格式
    log_format = '[%(levelname)s/%(asctime)s] %(name)s: %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(log_format, datefmt=date_format)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # 文件处理器（每次启动覆盖）
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # 添加处理器到根日志记录器
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # 为不同模块设置不同的日志级别
    logging.getLogger("pyrogram").setLevel(logging.WARNING)
    logging.getLogger("telethon").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    
    # 如果是调试模式，设置更详细的日志
    if settings.DEBUG:
        logging.getLogger("main").setLevel(logging.DEBUG)
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("日志系统初始化完成")
    logger.info(f"日志文件: {log_file}")
    logger.info(f"日志级别: {'DEBUG' if settings.DEBUG else 'INFO'}")
    logger.info(f"环境: {settings.ENVIRONMENT}")
    logger.info("=" * 60)


def get_logger(name: str) -> logging.Logger:
    """获取命名日志记录器"""
    return logging.getLogger(name)