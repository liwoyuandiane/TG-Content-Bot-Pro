"""配置验证器

提供配置验证功能，确保配置的完整性和正确性。
"""
import os
import re
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from ..config import settings, ConfigError

logger = logging.getLogger(__name__)


class ConfigValidator:
    """配置验证器类"""
    
    def __init__(self):
        """初始化配置验证器"""
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_all(self) -> bool:
        """验证所有配置项
        
        Returns:
            True表示所有配置验证通过，False表示存在错误
        """
        self.errors.clear()
        self.warnings.clear()
        
        # 验证基本配置
        self._validate_telegram_config()
        self._validate_database_config()
        self._validate_performance_config()
        self._validate_security_config()
        self._validate_environment_config()
        self._validate_additional_config()
        
        # 记录验证结果
        if self.errors:
            logger.error("配置验证失败，发现 %d 个错误", len(self.errors))
            for error in self.errors:
                logger.error("  • %s", error)
        
        if self.warnings:
            logger.warning("配置验证发现 %d 个警告", len(self.warnings))
            for warning in self.warnings:
                logger.warning("  • %s", warning)
        
        return len(self.errors) == 0
    
    def _validate_telegram_config(self) -> None:
        """验证Telegram相关配置"""
        # API_ID验证
        if not settings.API_ID:
            self.errors.append("API_ID 不能为空")
        elif not isinstance(settings.API_ID, int) or settings.API_ID <= 0:
            self.errors.append("API_ID 必须为正整数")
        
        # API_HASH验证
        if not settings.API_HASH:
            self.errors.append("API_HASH 不能为空")
        elif len(settings.API_HASH) != 32:
            self.errors.append(f"API_HASH 长度必须为32位，当前为 {len(settings.API_HASH)} 位")
        elif not settings.API_HASH.isalnum():
            self.errors.append("API_HASH 必须为字母数字组合")
        
        # BOT_TOKEN验证
        if not settings.BOT_TOKEN:
            self.errors.append("BOT_TOKEN 不能为空")
        elif not re.match(r'^\d+:[A-Za-z0-9_-]+$', settings.BOT_TOKEN):
            self.errors.append("BOT_TOKEN 格式无效，应为 '数字:字符串' 格式，例如：1234567890:ABCdefGhIJKLMNOPqrstUVwXYz123456")
        
        # AUTH验证
        if not settings.AUTH:
            self.errors.append("AUTH 不能为空")
        else:
            try:
                auth_users = settings.get_auth_users()
                if not auth_users:
                    self.errors.append("AUTH 必须包含有效的用户ID")
                for user_id in auth_users:
                    if not isinstance(user_id, int) or user_id <= 0:
                        self.errors.append(f"AUTH 中的用户ID {user_id} 无效，必须是正整数")
            except (ValueError, TypeError) as e:
                self.errors.append(f"AUTH 格式无效: {e}。正确格式应为：单个用户ID或逗号分隔的多个用户ID，例如：1234567890 或 1234567890,9876543210")
        
        # FORCESUB验证（可选）
        if hasattr(settings, 'FORCESUB') and settings.FORCESUB:
            # 检查FORCESUB格式，应为不含@的用户名
            if settings.FORCESUB.startswith('@'):
                self.warnings.append("FORCESUB 不应包含@符号，应为纯用户名")
            elif not re.match(r'^[a-zA-Z0-9_]+$', settings.FORCESUB):
                self.warnings.append("FORCESUB 格式无效，应为有效的Telegram用户名")
    
    def _validate_database_config(self) -> None:
        """验证数据库配置"""
        if not settings.MONGO_DB:
            self.errors.append("MONGO_DB 不能为空")
            return
        
        # 验证MongoDB连接字符串格式
        if not settings.MONGO_DB.startswith(('mongodb://', 'mongodb+srv://')):
            self.errors.append("MONGO_DB 必须是有效的MongoDB连接字符串，以 mongodb:// 或 mongodb+srv:// 开头")
        
        # 尝试解析连接字符串
        try:
            parsed = urlparse(settings.MONGO_DB)
            if not parsed.netloc:
                self.errors.append("MONGO_DB 连接字符串格式错误，无法解析主机名")
        except Exception as e:
            self.errors.append(f"MONGO_DB 连接字符串解析失败: {e}")
    
    def _validate_performance_config(self) -> None:
        """验证性能相关配置"""
        # 并发配置验证
        if settings.MAX_WORKERS <= 0 or settings.MAX_WORKERS > 20:
            self.errors.append(f"MAX_WORKERS 必须在1-20之间，当前为 {settings.MAX_WORKERS}")
        
        if settings.MIN_CONCURRENCY <= 0:
            self.errors.append(f"MIN_CONCURRENCY 必须大于0，当前为 {settings.MIN_CONCURRENCY}")
        
        if settings.MAX_CONCURRENCY < settings.MIN_CONCURRENCY:
            self.errors.append(f"MAX_CONCURRENCY ({settings.MAX_CONCURRENCY}) 不能小于 MIN_CONCURRENCY ({settings.MIN_CONCURRENCY})")
        
        if settings.MAX_CONCURRENCY > 50:
            self.warnings.append(f"MAX_CONCURRENCY ({settings.MAX_CONCURRENCY}) 过高，可能导致性能问题，建议不超过50")
        
        # 分块大小验证
        if settings.CHUNK_SIZE <= 0 or settings.CHUNK_SIZE > 50*1024*1024:
            self.errors.append(f"CHUNK_SIZE 必须在1字节到50MB之间，当前为 {settings.CHUNK_SIZE} 字节")
        elif settings.CHUNK_SIZE < 64*1024:
            self.warnings.append(f"CHUNK_SIZE 过小，建议至少64KB，当前为 {settings.CHUNK_SIZE} 字节")
        
        # 重试配置验证
        if settings.MAX_RETRIES <= 0 or settings.MAX_RETRIES > 10:
            self.errors.append(f"MAX_RETRIES 必须在1-10之间，当前为 {settings.MAX_RETRIES}")
        
        if settings.RETRY_DELAY <= 0:
            self.errors.append(f"RETRY_DELAY 必须大于0，当前为 {settings.RETRY_DELAY}")
        elif settings.RETRY_DELAY < 0.5:
            self.warnings.append(f"RETRY_DELAY 过小，建议至少0.5秒，当前为 {settings.RETRY_DELAY} 秒")
        
        # 超时配置验证
        if settings.CONNECT_TIMEOUT <= 0:
            self.errors.append(f"CONNECT_TIMEOUT 必须大于0，当前为 {settings.CONNECT_TIMEOUT}")
        elif settings.CONNECT_TIMEOUT < 10:
            self.warnings.append(f"CONNECT_TIMEOUT 过小，建议至少10秒，当前为 {settings.CONNECT_TIMEOUT} 秒")
        
        if settings.READ_TIMEOUT <= 0:
            self.errors.append(f"READ_TIMEOUT 必须大于0，当前为 {settings.READ_TIMEOUT}")
        elif settings.READ_TIMEOUT < 30:
            self.warnings.append(f"READ_TIMEOUT 过小，建议至少30秒，当前为 {settings.READ_TIMEOUT} 秒")
    
    def _validate_security_config(self) -> None:
        """验证安全相关配置"""
        # 流量限制验证
        if settings.DEFAULT_DAILY_LIMIT < 0:
            self.errors.append("DEFAULT_DAILY_LIMIT 不能为负数")
        
        if settings.DEFAULT_MONTHLY_LIMIT < 0:
            self.errors.append("DEFAULT_MONTHLY_LIMIT 不能为负数")
        
        if settings.DEFAULT_PER_FILE_LIMIT < 0:
            self.errors.append("DEFAULT_PER_FILE_LIMIT 不能为负数")
        
        # 加密密钥验证（如果存在）
        if settings.ENCRYPTION_KEY:
            key_length = len(settings.ENCRYPTION_KEY)
            if key_length < 3:
                self.errors.append(f"ENCRYPTION_KEY 长度过短，必须在3-128个字符之间，当前为 {key_length} 位")
            elif key_length > 128:
                self.errors.append(f"ENCRYPTION_KEY 长度过长，必须在3-128个字符之间，当前为 {key_length} 位")
            elif key_length < 16:
                self.warnings.append(f"ENCRYPTION_KEY 长度较短（{key_length} 位），建议至少16位以提高安全性")
            elif key_length < 32:
                self.warnings.append(f"ENCRYPTION_KEY 长度建议至少32位以提高安全性，当前为 {key_length} 位")
    
    def _validate_environment_config(self) -> None:
        """验证环境相关配置"""
        # 环境验证
        if settings.ENVIRONMENT not in ['development', 'testing', 'production']:
            self.errors.append(f"ENVIRONMENT 必须是 development、testing 或 production，当前为 {settings.ENVIRONMENT}")
        
        # 日志级别验证
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        log_level_upper = settings.LOG_LEVEL.upper()
        if log_level_upper not in valid_log_levels:
            self.errors.append(f"LOG_LEVEL 必须是 {', '.join(valid_log_levels)} 之一，当前为 {settings.LOG_LEVEL}")
        
        # 健康检查端口验证
        if not (1024 <= settings.HEALTH_CHECK_PORT <= 65535):
            self.errors.append(f"HEALTH_CHECK_PORT 必须在1024-65535之间，当前为 {settings.HEALTH_CHECK_PORT}")
    
    def _validate_additional_config(self) -> None:
        """验证其他配置项"""
        # SESSION验证（可选）
        if hasattr(settings, 'SESSION') and settings.SESSION:
            # 简单验证SESSION长度
            if len(settings.SESSION) < 50:
                self.warnings.append("SESSION 长度过短，可能无效")
    
    def get_validation_report(self) -> Dict[str, Any]:
        """获取验证报告
        
        Returns:
            包含验证结果的字典
        """
        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors.copy(),
            "warnings": self.warnings.copy(),
            "error_count": len(self.errors),
            "warning_count": len(self.warnings)
        }
    
    def generate_config_template(self) -> Dict[str, Any]:
        """生成配置模板
        
        Returns:
            配置模板字典
        """
        return {
            # 必需配置项
            "API_ID": "your_api_id_here",  # 从 my.telegram.org 获取
            "API_HASH": "your_api_hash_here",  # 从 my.telegram.org 获取
            "BOT_TOKEN": "your_bot_token_here",  # 从 @BotFather 获取
            "AUTH": "your_user_id_here",  # 从 @userinfobot 获取，支持多个ID逗号分隔
            "MONGO_DB": "your_mongodb_connection_string",  # MongoDB连接字符串
            
            # 可选配置项
            "SESSION": "",  # Pyrogram会话字符串
            "FORCESUB": "",  # 强制订阅频道（不含@）
            "ENCRYPTION_KEY": "",  # 加密密钥，可选
            
            # 环境配置
            "ENVIRONMENT": "production",  # development, testing, production
            "LOG_LEVEL": "INFO",  # DEBUG, INFO, WARNING, ERROR, CRITICAL
            
            # 性能配置
            "MAX_WORKERS": 3,  # 工作线程数（1-20）
            "MIN_CONCURRENCY": 1,  # 最小并发数
            "MAX_CONCURRENCY": 15,  # 最大并发数
            "CHUNK_SIZE": 524288,  # 分块大小（1-50MB）
            "MAX_RETRIES": 3,  # 最大重试次数（1-10）
            "RETRY_DELAY": 1.0,  # 重试延迟（秒）
            "CONNECT_TIMEOUT": 30,  # 连接超时（秒）
            "READ_TIMEOUT": 60,  # 读取超时（秒）
            
            # 流量限制配置
            "DEFAULT_DAILY_LIMIT": 1073741824,  # 默认每日流量限制（字节，1GB）
            "DEFAULT_MONTHLY_LIMIT": 10737418240,  # 默认每月流量限制（字节，10GB）
            "DEFAULT_PER_FILE_LIMIT": 104857600,  # 默认单文件限制（字节，100MB）
            
            # 健康检查配置
            "HEALTH_CHECK_PORT": 28089  # 健康检查端口（1024-65535）
        }
    
    def generate_env_file_template(self) -> str:
        """生成.env文件模板
        
        Returns:
            .env文件内容字符串
        """
        template = "# TG-Content-Bot-Pro 配置文件\n# 请根据实际情况修改以下配置\n\n"
        
        config_template = self.generate_config_template()
        for key, value in config_template.items():
            if isinstance(value, str) and 'your_' in value:
                template += f"{key}={value}\n"
            else:
                template += f"{key}={value}\n"
        
        return template


def ensure_config_integrity() -> bool:
    """确保配置完整性"""
    try:
        validator = ConfigValidator()
        is_valid = validator.validate_all()
        if not is_valid:
            report = validator.get_validation_report()
            logger.error("配置完整性检查失败，发现 %d 个错误", report["error_count"])
        return is_valid
    except Exception as e:
        logger.error("配置完整性检查时发生错误: %s", e)
        return False