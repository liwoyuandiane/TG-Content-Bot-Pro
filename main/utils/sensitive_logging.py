"""
敏感信息日志过滤工具
提供安全的日志记录功能，自动过滤敏感信息如SESSION字符串、API密钥等
"""
import logging
import re
from typing import Any, Dict, List, Pattern
from logging import LogRecord


class SensitiveFilter(logging.Filter):
    """敏感信息日志过滤器"""
    
    def __init__(self, name: str = ""):
        super().__init__(name)
        self._sensitive_patterns: List[Pattern] = []
        self._initialize_patterns()
    
    def _initialize_patterns(self):
        """初始化敏感信息匹配模式"""
        # SESSION字符串模式（Telegram SESSION字符串通常是base64格式）
        session_patterns = [
            r'(session[\s=:"\']+)([A-Za-z0-9+/]{40,}={0,2})',  # base64格式
            r'(1[\s=:"\']+)([A-Za-z0-9+/]{40,}={0,2})',      # 以1开头的SESSION
        ]
        
        # API密钥和令牌模式
        api_patterns = [
            r'(api[_-]?key[\s=:"\']+)([A-Za-z0-9]{32,64})',      # API密钥
            r'(bot[\s]*token[\s=:"\']+)([0-9]+:[A-Za-z0-9_-]{35})',  # Bot Token
            r'(token[\s=:"\']+)([A-Za-z0-9]{32,64})',               # 通用令牌
        ]
        
        # 数据库连接字符串
        db_patterns = [
            r'(mongodb[\s=:"\']+)([^\s"\']+)',              # MongoDB连接字符串
            r'(username[\s=:"\']+)([^\s"\']+)',             # 用户名
            r'(password[\s=:"\']+)([^\s"\']+)',             # 密码
            r'(host[\s=:"\']+)([^\s"\']+)',                 # 主机
            r'(port[\s=:"\']+)([0-9]+)',                    # 端口
        ]
        
        # 加密密钥
        encryption_patterns = [
            r'(encryption[\s]*key[\s=:"\']+)([A-Za-z0-9]{32,64})',  # 加密密钥
            r'(secret[\s=:"\']+)([A-Za-z0-9]{32,64})',              # 密钥
        ]
        
        # 用户敏感信息
        user_patterns = [
            r'(phone[\s=:"\']+)(\+?[0-9]{10,15})',          # 手机号
            r'(email[\s=:"\']+)([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})',  # 邮箱
            r'(user[\s]*id[\s=:"\']+)([0-9]+)',            # 用户ID
        ]
        
        # 合并所有模式
        all_patterns = (
            session_patterns + 
            api_patterns + 
            db_patterns + 
            encryption_patterns + 
            user_patterns
        )
        
        for pattern in all_patterns:
            try:
                self._sensitive_patterns.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                logging.warning(f"无效的正则表达式模式: {pattern}, 错误: {e}")
    
    def filter(self, record: LogRecord) -> bool:
        """过滤日志记录中的敏感信息"""
        if hasattr(record, 'msg') and record.msg:
            record.msg = self._sanitize_message(str(record.msg))
        
        if hasattr(record, 'args') and record.args:
            record.args = self._sanitize_args(record.args)
        
        return True
    
    def _sanitize_message(self, message: str) -> str:
        """清理消息中的敏感信息"""
        if not message:
            return message
        
        sanitized = message
        
        for pattern in self._sensitive_patterns:
            try:
                # 使用替换函数来保留前缀但隐藏敏感数据
                sanitized = pattern.sub(
                    lambda m: f"{m.group(1)}[REDACTED:{self._get_data_type(m.group(2))}]",
                    sanitized
                )
            except Exception as e:
                # 如果正则替换出错，保持原消息
                logging.debug(f"正则替换出错: {e}")
        
        return sanitized
    
    def _sanitize_args(self, args: Any) -> Any:
        """清理参数中的敏感信息"""
        if isinstance(args, (tuple, list)):
            return tuple(self._sanitize_arg(arg) for arg in args)
        elif isinstance(args, dict):
            return {k: self._sanitize_arg(v) for k, v in args.items()}
        else:
            return self._sanitize_arg(args)
    
    def _sanitize_arg(self, arg: Any) -> Any:
        """清理单个参数"""
        if isinstance(arg, str):
            return self._sanitize_message(arg)
        elif isinstance(arg, (dict, list, tuple)):
            return self._sanitize_args(arg)
        else:
            return arg
    
    def _get_data_type(self, data: str) -> str:
        """根据数据特征判断数据类型"""
        if len(data) >= 40 and re.match(r'^[A-Za-z0-9+/]+={0,2}$', data):
            return "SESSION"
        elif re.match(r'^[0-9]+:[A-Za-z0-9_-]{35}$', data):
            return "BOT_TOKEN"
        elif len(data) >= 32 and re.match(r'^[A-Za-z0-9]+$', data):
            return "API_KEY"
        elif re.match(r'^\+?[0-9]{10,15}$', data):
            return "PHONE"
        elif re.match(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$', data):
            return "EMAIL"
        elif re.match(r'^mongodb://', data):
            return "DB_CONNECTION"
        else:
            return "SENSITIVE_DATA"


def setup_sensitive_logging():
    """设置敏感信息日志过滤"""
    # 获取根日志器
    root_logger = logging.getLogger()
    
    # 创建敏感信息过滤器
    sensitive_filter = SensitiveFilter()
    
    # 为所有处理器添加过滤器
    for handler in root_logger.handlers:
        handler.addFilter(sensitive_filter)
    
    # 为根日志器添加过滤器
    root_logger.addFilter(sensitive_filter)


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """清理字典中的敏感信息"""
    sensitive_keys = {
        'session', 'session_string', 'session_str',
        'api_id', 'api_hash', 'bot_token', 'token',
        'username', 'password', 'host', 'port',
        'encryption_key', 'secret',
        'phone', 'email', 'user_id'
    }
    
    sanitized = {}
    
    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            sanitized[key] = f"[REDACTED:{key.upper()}]"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        elif isinstance(value, (list, tuple)):
            sanitized[key] = [sanitize_dict(item) if isinstance(item, dict) else 
                            f"[REDACTED:LIST_ITEM]" if isinstance(item, str) and len(item) > 20 else item
                            for item in value]
        elif isinstance(value, str) and len(value) > 30:
            # 对于长字符串，检查是否包含敏感信息
            if any(pattern.search(value) for pattern in SensitiveFilter()._sensitive_patterns):
                sanitized[key] = f"[REDACTED:LONG_STRING]"
            else:
                sanitized[key] = value
        else:
            sanitized[key] = value
    
    return sanitized


def log_safely(message: str, *args, level: int = logging.INFO, **kwargs):
    """安全日志记录函数"""
    logger = logging.getLogger(__name__)
    
    # 清理消息和参数
    safe_message = SensitiveFilter()._sanitize_message(message)
    safe_args = SensitiveFilter()._sanitize_args(args)
    safe_kwargs = SensitiveFilter()._sanitize_args(kwargs)
    
    # 记录日志
    logger.log(level, safe_message, *safe_args, **safe_kwargs)


class SafeLogger:
    """安全日志记录器"""
    
    def __init__(self, name: str = None):
        self.logger = logging.getLogger(name)
        self.filter = SensitiveFilter()
    
    def debug(self, msg, *args, **kwargs):
        safe_msg = self.filter._sanitize_message(msg)
        safe_args = self.filter._sanitize_args(args)
        safe_kwargs = self.filter._sanitize_args(kwargs)
        self.logger.debug(safe_msg, *safe_args, **safe_kwargs)
    
    def info(self, msg, *args, **kwargs):
        safe_msg = self.filter._sanitize_message(msg)
        safe_args = self.filter._sanitize_args(args)
        safe_kwargs = self.filter._sanitize_args(kwargs)
        self.logger.info(safe_msg, *safe_args, **safe_kwargs)
    
    def warning(self, msg, *args, **kwargs):
        safe_msg = self.filter._sanitize_message(msg)
        safe_args = self.filter._sanitize_args(args)
        safe_kwargs = self.filter._sanitize_args(kwargs)
        self.logger.warning(safe_msg, *safe_args, **safe_kwargs)
    
    def error(self, msg, *args, **kwargs):
        safe_msg = self.filter._sanitize_message(msg)
        safe_args = self.filter._sanitize_args(args)
        safe_kwargs = self.filter._sanitize_args(kwargs)
        self.logger.error(safe_msg, *safe_args, **safe_kwargs)
    
    def exception(self, msg, *args, **kwargs):
        safe_msg = self.filter._sanitize_message(msg)
        safe_args = self.filter._sanitize_args(args)
        safe_kwargs = self.filter._sanitize_args(kwargs)
        self.logger.exception(safe_msg, *safe_args, **safe_kwargs)