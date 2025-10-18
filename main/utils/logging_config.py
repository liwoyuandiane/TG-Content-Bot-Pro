"""日志配置模块"""
import logging
import os
from logging.handlers import RotatingFileHandler
from ..config import settings


def setup_logging():
    """设置日志配置"""
    # 创建日志目录
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 配置根日志记录器
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # 控制台处理器
            logging.StreamHandler(),
            # 文件处理器（轮转日志）
            RotatingFileHandler(
                filename=os.path.join(log_dir, "app.log"),
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
        ]
    )
    
    # 为不同模块设置不同的日志级别
    logging.getLogger("pyrogram").setLevel(logging.WARNING)
    logging.getLogger("telethon").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    
    # 如果是调试模式，设置更详细的日志
    if settings.DEBUG:
        logging.getLogger("main").setLevel(logging.DEBUG)
    
    logger = logging.getLogger(__name__)
    logger.info("日志系统初始化完成")
    logger.info(f"日志级别: {'DEBUG' if settings.DEBUG else 'INFO'}")
    logger.info(f"环境: {settings.ENVIRONMENT}")


def get_logger(name: str) -> logging.Logger:
    """获取命名日志记录器"""
    return logging.getLogger(name)