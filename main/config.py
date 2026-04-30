"""配置管理模块

该模块提供应用的配置管理功能，包括环境变量加载、配置验证和运行时配置管理。
"""
import logging
import re
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
        
        从环境变量加载所有配置项，增加类型转换和格式验证。
        """
        # Telegram API 配置
        self.API_ID: int = self._get_config("API_ID", cast=int)
        self.API_HASH: str = self._get_config("API_HASH", cast=str)
        self.BOT_TOKEN: str = self._get_config("BOT_TOKEN", cast=str)
        # 特殊处理SESSION配置，避免将None默认值转换为"None"字符串
        session_value = self._get_config("SESSION", default=None)
        self.SESSION: Optional[str] = session_value if session_value is None else str(session_value)
        self.FORCESUB: Optional[str] = self._get_config("FORCESUB", default=None, cast=str)
        self.AUTH: Union[int, str] = self._get_config("AUTH", cast=str)  # 支持逗号分隔的用户ID
        
        # 数据库配置
        self.MONGO_DB: Optional[str] = self._get_config("MONGO_DB", default=None, cast=str)
        
        # 安全配置
        self.ENCRYPTION_KEY: Optional[str] = self._get_config("ENCRYPTION_KEY", default=None, cast=str)
        

        
        # 性能配置
        self.MAX_WORKERS: int = self._get_config("MAX_WORKERS", default=3, cast=int)
        self.MIN_CONCURRENCY: int = self._get_config("MIN_CONCURRENCY", default=1, cast=int)
        self.MAX_CONCURRENCY: int = self._get_config("MAX_CONCURRENCY", default=15, cast=int)
        self.CHUNK_SIZE: int = self._get_config("CHUNK_SIZE", default=512*1024, cast=int)  # 512KB，优化内存使用
        
        # 流量限制配置
        self.DEFAULT_DAILY_LIMIT: int = self._get_config("DEFAULT_DAILY_LIMIT", default=1073741824, cast=int)  # 1GB
        self.DEFAULT_MONTHLY_LIMIT: int = self._get_config("DEFAULT_MONTHLY_LIMIT", default=10737418240, cast=int)  # 10GB
        self.DEFAULT_PER_FILE_LIMIT: int = self._get_config("DEFAULT_PER_FILE_LIMIT", default=104857600, cast=int)  # 100MB
        
        # 环境配置
        self.ENVIRONMENT: str = self._get_config("ENVIRONMENT", default="production")  # 默认生产环境
        self.DEBUG: bool = self._get_config("DEBUG", default=False, cast=bool)
        
        # 日志配置
        self.LOG_LEVEL: str = self._get_config("LOG_LEVEL", default="INFO")
        self.LOG_FILE: Optional[str] = self._get_config("LOG_FILE", default=None)
        
        # 健康检查配置
        self.HEALTH_CHECK_PORT: int = self._get_config("HEALTH_CHECK_PORT", default=28089, cast=int)
        
        # 重试配置
        self.MAX_RETRIES: int = self._get_config("MAX_RETRIES", default=3, cast=int)
        self.RETRY_DELAY: float = self._get_config("RETRY_DELAY", default=1.0, cast=float)
        
        # 连接超时配置
        self.CONNECT_TIMEOUT: int = self._get_config("CONNECT_TIMEOUT", default=30, cast=int)
        self.READ_TIMEOUT: int = self._get_config("READ_TIMEOUT", default=60, cast=int)
        
        # 批量处理限制配置
        self.FREEMIUM_LIMIT: int = self._get_config("FREEMIUM_LIMIT", default=0, cast=int)  # 免费用户不能批量
        self.PREMIUM_LIMIT: int = self._get_config("PREMIUM_LIMIT", default=10, cast=int)
    
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
        
        验证配置项的有效性，增加格式和业务逻辑验证。
        
        Raises:
            ConfigError: 当配置验证失败时
        """
        if self._validated:
            return
        
        errors: List[str] = []
        
        # 验证必需配置
        if not self.API_ID:
            errors.append("API_ID 不能为空")
        elif not isinstance(self.API_ID, int) or self.API_ID <= 0:
            errors.append("API_ID 必须为正整数")
            
        if not self.API_HASH:
            errors.append("API_HASH 不能为空")
        elif len(self.API_HASH) != 32:
            errors.append("API_HASH 长度必须为32位")
            
        if not self.BOT_TOKEN:
            errors.append("BOT_TOKEN 不能为空")
        elif not re.match(r'^\d+:[A-Za-z0-9_-]+$', self.BOT_TOKEN):
            errors.append(f"BOT_TOKEN 格式无效，应为 '数字:字符串' 格式。当前值: '{self.BOT_TOKEN[:20]}...' 长度: {len(self.BOT_TOKEN)}")
            
        if not self.AUTH:
            errors.append("AUTH 不能为空")
        else:
            # 验证AUTH格式（可以是单个数字或逗号分隔的数字列表）
            try:
                auth_users = self.get_auth_users()
                if not auth_users:
                    errors.append("AUTH 必须包含有效的用户ID")
                for user_id in auth_users:
                    if not isinstance(user_id, int) or user_id <= 0:
                        errors.append(f"AUTH 中的用户ID {user_id} 无效")
            except (ValueError, TypeError) as e:
                errors.append(f"AUTH 格式无效: {e}")
        
        # 代理配置验证 - 简化逻辑：代理配置是可选的，只有设置了完整的代理配置时才使用
        # 如果用户设置了部分代理配置，会在运行时进行检测和处理
        # 这里不进行强制验证，避免误报
        
        # 验证数据库连接字符串
        if self.MONGO_DB:
            if not self.MONGO_DB.startswith(('mongodb://', 'mongodb+srv://')):
                errors.append("MONGO_DB 必须是有效的MongoDB连接字符串")
        
        # 验证数值配置
        if self.MAX_WORKERS <= 0 or self.MAX_WORKERS > 20:
            errors.append("MAX_WORKERS 必须在1-20之间")
        if self.CHUNK_SIZE <= 0 or self.CHUNK_SIZE > 10*1024*1024:
            errors.append("CHUNK_SIZE 必须在1字节到10MB之间")
        if self.DEFAULT_DAILY_LIMIT < 0:
            errors.append("DEFAULT_DAILY_LIMIT 不能为负数")
        if self.DEFAULT_MONTHLY_LIMIT < 0:
            errors.append("DEFAULT_MONTHLY_LIMIT 不能为负数")
        if self.DEFAULT_PER_FILE_LIMIT < 0:
            errors.append("DEFAULT_PER_FILE_LIMIT 不能为负数")
        if self.MAX_CONCURRENCY < self.MIN_CONCURRENCY:
            errors.append("MAX_CONCURRENCY 不能小于 MIN_CONCURRENCY")
        if self.MAX_RETRIES <= 0 or self.MAX_RETRIES > 10:
            errors.append("MAX_RETRIES 必须在1-10之间")
        if self.RETRY_DELAY <= 0:
            errors.append("RETRY_DELAY 必须大于0")
        if self.CONNECT_TIMEOUT <= 0:
            errors.append("CONNECT_TIMEOUT 必须大于0")
        if self.READ_TIMEOUT <= 0:
            errors.append("READ_TIMEOUT 必须大于0")
        
        # 验证健康检查端口
        if self.HEALTH_CHECK_PORT < 1024 or self.HEALTH_CHECK_PORT > 65535:
            errors.append("HEALTH_CHECK_PORT 必须在 1024-65535 范围内")
        
        # 验证批量处理限制
        if self.FREEMIUM_LIMIT < 0:
            errors.append("FREEMIUM_LIMIT 不能为负数")
        if self.PREMIUM_LIMIT < 0:
            errors.append("PREMIUM_LIMIT 不能为负数")
        if self.FREEMIUM_LIMIT > self.PREMIUM_LIMIT:
            errors.append("FREEMIUM_LIMIT 不能大于 PREMIUM_LIMIT")
        
        # 验证环境配置
        if self.ENVIRONMENT not in ['development', 'testing', 'production']:
            errors.append("ENVIRONMENT 必须是 development、testing 或 production")
        
        # 验证日志级别
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.LOG_LEVEL.upper() not in valid_log_levels:
            errors.append(f"LOG_LEVEL 必须是 {', '.join(valid_log_levels)} 之一")
        
        if errors:
            error_details = "\n".join([f"  • {error}" for error in errors])
            raise ConfigError(f"配置验证失败:\n{error_details}")
        
        self._validated = True
        logger.info("配置验证通过，共检查 %d 个配置项", len(errors) + 18)  # 估算检查的配置项数量
    
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
    
    def get_retry_config(self) -> Dict[str, Any]:
        """获取重试配置
        
        Returns:
            重试配置字典
        """
        return {
            "max_retries": self.MAX_RETRIES,
            "retry_delay": self.RETRY_DELAY,
            "connect_timeout": self.CONNECT_TIMEOUT,
            "read_timeout": self.READ_TIMEOUT
        }
    
    def is_production(self) -> bool:
        """检查是否为生产环境
        
        Returns:
            True表示生产环境，False表示开发/测试环境
        """
        return self.ENVIRONMENT.lower() == "production"
    
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
        """检查用户是否被授权"""
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
    
    def get_batch_limits(self) -> Dict[str, int]:
        """获取批量处理限制配置
        
        Returns:
            包含批量处理限制配置的字典
        """
        return {
            "freemium_limit": self.FREEMIUM_LIMIT,
            "premium_limit": self.PREMIUM_LIMIT
        }
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """将配置转换为字典
        
        Args:
            include_sensitive: 是否包含敏感信息（如密码、Token等）
            
        Returns:
            包含所有配置项的字典
        """
        config_dict = {
            "API_ID": self.API_ID,
            "API_HASH": "***" if not include_sensitive else self.API_HASH,
            "BOT_TOKEN": "***" if not include_sensitive else self.BOT_TOKEN,
            "SESSION": "***" if self.SESSION and not include_sensitive else self.SESSION,
            "FORCESUB": self.FORCESUB,
            "AUTH": self.AUTH,
            "MONGO_DB": "***" if self.MONGO_DB and not include_sensitive else self.MONGO_DB,
            "ENCRYPTION_KEY": "***" if self.ENCRYPTION_KEY and not include_sensitive else self.ENCRYPTION_KEY,

            "MAX_WORKERS": self.MAX_WORKERS,
            "MIN_CONCURRENCY": self.MIN_CONCURRENCY,
            "MAX_CONCURRENCY": self.MAX_CONCURRENCY,
            "CHUNK_SIZE": self.CHUNK_SIZE,
            "DEFAULT_DAILY_LIMIT": self.DEFAULT_DAILY_LIMIT,
            "DEFAULT_MONTHLY_LIMIT": self.DEFAULT_MONTHLY_LIMIT,
            "DEFAULT_PER_FILE_LIMIT": self.DEFAULT_PER_FILE_LIMIT,
            "ENVIRONMENT": self.ENVIRONMENT,
            "DEBUG": self.DEBUG,
            "LOG_LEVEL": self.LOG_LEVEL,
            "LOG_FILE": self.LOG_FILE,
            "HEALTH_CHECK_PORT": self.HEALTH_CHECK_PORT,
            "MAX_RETRIES": self.MAX_RETRIES,
            "RETRY_DELAY": self.RETRY_DELAY,
            "CONNECT_TIMEOUT": self.CONNECT_TIMEOUT,
            "READ_TIMEOUT": self.READ_TIMEOUT,
            "FREEMIUM_LIMIT": self.FREEMIUM_LIMIT,
            "PREMIUM_LIMIT": self.PREMIUM_LIMIT
        }
        
        return config_dict
    
    def get_safe_summary(self) -> Dict[str, Any]:
        """获取安全的配置摘要（不包含敏感信息）
        
        Returns:
            安全的配置摘要字典
        """
        return self.to_dict(include_sensitive=False)
    
    def validate_bot_token_format(self, token: str) -> bool:
        """验证Bot Token格式
        
        Args:
            token: 要验证的Bot Token
            
        Returns:
            True表示格式正确，False表示格式错误
        """
        return bool(re.match(r'^\d+:\w+$', token))
    
    def validate_api_hash_format(self, api_hash: str) -> bool:
        """验证API Hash格式
        
        Args:
            api_hash: 要验证的API Hash
            
        Returns:
            True表示格式正确，False表示格式错误
        """
        return len(api_hash) == 32 and api_hash.isalnum()
    
    def get_config_summary(self) -> str:
        """获取配置摘要字符串
        
        Returns:
            配置摘要字符串
        """
        safe_config = self.get_safe_summary()
        summary_lines = ["配置摘要:"]
        
        for key, value in safe_config.items():
            if value is not None:
                summary_lines.append(f"  {key}: {value}")
        
        return "\n".join(summary_lines)


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