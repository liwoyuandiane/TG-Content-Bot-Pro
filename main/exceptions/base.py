"""基础异常类"""


class BaseBotException(Exception):
    """基础异常类"""
    
    def __init__(self, message: str, code: str = "UNKNOWN_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code