"""验证相关异常"""
from .base import BaseBotException


class ValidationException(BaseBotException):
    """验证异常"""
    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")


class TrafficLimitException(BaseBotException):
    """流量限制异常"""
    def __init__(self, message: str):
        super().__init__(message, "TRAFFIC_LIMIT_ERROR")