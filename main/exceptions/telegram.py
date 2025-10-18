"""Telegram相关异常"""
from .base import BaseBotException


class TelegramAPIException(BaseBotException):
    """Telegram API 异常"""
    def __init__(self, message: str):
        super().__init__(message, "TELEGRAM_API_ERROR")


class SessionException(BaseBotException):
    """会话相关异常"""
    def __init__(self, message: str):
        super().__init__(message, "SESSION_ERROR")


class ChannelAccessException(BaseBotException):
    """频道访问异常"""
    def __init__(self, message: str):
        super().__init__(message, "CHANNEL_ACCESS_ERROR")