"""配置管理模块

该模块提供应用的配置管理功能，包括环境变量加载、配置验证和运行时配置管理。
"""
import os
import logging
from typing import Optional, Any, Dict, List, Union
from decouple import config, undefined

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """配置错误异常
    
    当配置加载或验证失败时抛出此异常。
    """
    pass


class Settings:
    """应用配置类
    
    负责加载、验证和管理应用的所有配置项。
    配置来源包括环境变量和运行时配置文件。
    """
    
    def __init__(self) -> None:
        """初始化配置管理器"""
        self._validated: bool = False
        self._load_settings()
        self._validate_settings()
    
    def _load_settings(self) -> None:
        """加载配置
        
        从环境变量加载所有配置项。
        """
        # Telegram API 配置
        self.API_ID: int = self._get_config("API_ID", cast=int)
        self.API_HASH: str = self._get_config("API_HASH", cast=str)
        self.BOT_TOKEN: str = self._get_config("BOT_TOKEN", cast=str)
        self.SESSION: Optional[str] = self._get_config("SESSION", default=None, cast=str)
        self.FORCESUB: Optional[str] = self._get_config("FORCESUB", default=None, cast=str)
        self.AUTH: int = self._get_config("AUTH", cast=int)
        
        # 数据库配置
        self.MONGO_DB: Optional[str] = self._get_config("MONGO_DB", default=None, cast=str)
        
        # 安全配置
        self.ENCRYPTION_KEY: Optional[str] = self._get_config("ENCRYPTION_KEY", default=None, cast=str)
        
        # 性能配置
        self.MAX_WORKERS: int = self._get_config("MAX_WORKERS", default=3, cast=int)
        self.CHUNK_SIZE: int = self._get_config("CHUNK_SIZE", default=1024*1024, cast=int)  # 1MB
        
        # 流量限制配置
        self.DEFAULT_DAILY_LIMIT: int = self._get_config("DEFAULT_DAILY_LIMIT", default=1073741824, cast=int)  # 1GB
        self.DEFAULT_MONTHLY_LIMIT: int = self._get_config("DEFAULT_MONTHLY_LIMIT", default=10737418240, cast=int)  # 10GB
        self.DEFAULT_PER_FILE_LIMIT: int = self._get_config("DEFAULT_PER_FILE_LIMIT", default=104857600, cast=int)  # 100MB
        
        # 环境配置
        self.ENVIRONMENT: str = self._get_config("ENVIRONMENT", default="development")
        self.DEBUG: bool = self._get_config("DEBUG", default=False, cast=bool)
        
        # 日志配置
        self.LOG_LEVEL: str = self._get_config("LOG_LEVEL", default="INFO")
        self.LOG_FILE: Optional[str] = self._get_config("LOG_FILE", default=None)
    
    def _get_config(self, key: str, default: Any = undefined, cast: Optional[Any] = None) -> Any:
        """获取配置值
        
        Args:
            key: 配置项键名
            default: 默认值
            cast: 类型转换函数
            
        Returns:
            配置项的值
            
        Raises:
            ConfigError: 当必需的配置项缺失时
        """
        try:
            if default is undefined:
                return config(key, cast=cast)
            else:
                return config(key, default=default, cast=cast)
        except Exception as e:
            if default is undefined:
                raise ConfigError(f"缺少必需的配置项: {key}") from e
            return default
    
    def _validate_settings(self) -> None:
        """验证配置
        
        验证配置项的有效性。
        
        Raises:
            ConfigError: 当配置验证失败时
        """
        if self._validated:
            return
        
        errors: List[str] = []
        
        # 验证必需配置
        if not self.API_ID:
            errors.append("API_ID 不能为空")
        if not self.API_HASH:
            errors.append("API_HASH 不能为空")
        if not self.BOT_TOKEN:
            errors.append("BOT_TOKEN 不能为空")
        if not self.AUTH:
            errors.append("AUTH 不能为空")
        
        # 验证数值配置
        if self.MAX_WORKERS <= 0:
            errors.append("MAX_WORKERS 必须大于0")
        if self.CHUNK_SIZE <= 0:
            errors.append("CHUNK_SIZE 必须大于0")
        if self.DEFAULT_DAILY_LIMIT < 0:
            errors.append("DEFAULT_DAILY_LIMIT 不能为负数")
        if self.DEFAULT_MONTHLY_LIMIT < 0:
            errors.append("DEFAULT_MONTHLY_LIMIT 不能为负数")
        if self.DEFAULT_PER_FILE_LIMIT < 0:
            errors.append("DEFAULT_PER_FILE_LIMIT 不能为负数")
        
        if errors:
            raise ConfigError("配置验证失败:\n" + "\n".join(errors))
        
        self._validated = True
        logger.info("配置验证通过")
    
    def get_database_url(self) -> Optional[str]:
        """获取数据库URL
        
        Returns:
            数据库连接URL，如果未配置则返回None
        """
        return self.MONGO_DB
    
    def is_debug_mode(self) -> bool:
        """检查是否为调试模式
        
        Returns:
            True表示调试模式，False表示生产模式
        """
        return self.DEBUG
    
    def get_environment(self) -> str:
        """获取环境名称
        
        Returns:
            环境名称（development, production等）
        """
        return self.ENVIRONMENT
    
    def get_auth_users(self) -> List[int]:
        """获取授权用户列表
        
        Returns:
            授权用户ID列表
        """
        # AUTH 可能是单个用户ID或逗号分隔的多个用户ID
        if isinstance(self.AUTH, str):
            return [int(uid.strip()) for uid in self.AUTH.split(",") if uid.strip()]
        else:
            return [self.AUTH]
    
    def is_user_authorized(self, user_id: int) -> bool:
        """检查用户是否被授权
        
        Args:
            user_id: 用户ID
            
        Returns:
            True表示用户被授权，False表示未授权
        """
        return user_id in self.get_auth_users()
    
    def get_traffic_limits(self) -> Dict[str, int]:
        """获取流量限制配置
        
        Returns:
            包含流量限制配置的字典
        """
        return {
            "daily_limit": self.DEFAULT_DAILY_LIMIT,
            "monthly_limit": self.DEFAULT_MONTHLY_LIMIT,
            "per_file_limit": self.DEFAULT_PER_FILE_LIMIT
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典
        
        Returns:
            包含所有配置项的字典
        """
        return {
            "API_ID": self.API_ID,
            "API_HASH": self.API_HASH,
            "BOT_TOKEN": self.BOT_TOKEN,
            "SESSION": self.SESSION,
            "FORCESUB": self.FORCESUB,
            "AUTH": self.AUTH,
            "MONGO_DB": self.MONGO_DB,
            "ENCRYPTION_KEY": self.ENCRYPTION_KEY,
            "MAX_WORKERS": self.MAX_WORKERS,
            "CHUNK_SIZE": self.CHUNK_SIZE,
            "DEFAULT_DAILY_LIMIT": self.DEFAULT_DAILY_LIMIT,
            "DEFAULT_MONTHLY_LIMIT": self.DEFAULT_MONTHLY_LIMIT,
            "DEFAULT_PER_FILE_LIMIT": self.DEFAULT_PER_FILE_LIMIT,
            "ENVIRONMENT": self.ENVIRONMENT,
            "DEBUG": self.DEBUG,
            "LOG_LEVEL": self.LOG_LEVEL,
            "LOG_FILE": self.LOG_FILE
        }


# 创建全局配置实例
try:
    settings: Settings = Settings()
    logger.info("配置加载完成")
except ConfigError as e:
    logger.error(f"配置加载失败: {e}")
    raise
except Exception as e:
    logger.error(f"配置加载时发生未知错误: {e}")
    raise