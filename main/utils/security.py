"""安全工具模块"""
import hashlib
import secrets
import logging
from typing import Optional, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

logger = logging.getLogger(__name__)


class SecurityManager:
    """安全管理器"""
    
    def __init__(self):
        self._fernet = None
    
    def generate_encryption_key(self) -> str:
        """生成新的加密密钥"""
        return Fernet.generate_key().decode()
    
    def derive_key_from_password(self, password: str, salt: Optional[bytes] = None) -> Tuple[str, bytes]:
        """从密码派生加密密钥"""
        if salt is None:
            salt = secrets.token_bytes(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key.decode(), salt
    
    def hash_password(self, password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """哈希密码"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return password_hash.hex(), salt
    
    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """验证密码"""
        hashed, _ = self.hash_password(password, salt)
        return secrets.compare_digest(hashed, password_hash)
    
    def generate_secure_token(self, length: int = 32) -> str:
        """生成安全令牌"""
        return secrets.token_urlsafe(length)
    
    def generate_session_id(self) -> str:
        """生成会话ID"""
        return secrets.token_urlsafe(32)
    
    def mask_sensitive_data(self, data: str, show_chars: int = 4) -> str:
        """掩码敏感数据"""
        if len(data) <= show_chars * 2:
            return "*" * len(data)
        return data[:show_chars] + "*" * (len(data) - show_chars * 2) + data[-show_chars:]
    
    def sanitize_input(self, input_str: str) -> str:
        """清理输入数据"""
        # 移除潜在的危险字符
        dangerous_chars = ['<', '>', '&', '"', "'", '`']
        for char in dangerous_chars:
            input_str = input_str.replace(char, '')
        return input_str.strip()


# 全局安全管理器实例
security_manager = SecurityManager()


def generate_encryption_key() -> str:
    """生成加密密钥的便捷函数"""
    return security_manager.generate_encryption_key()


def hash_password(password: str) -> Tuple[str, str]:
    """哈希密码的便捷函数"""
    return security_manager.hash_password(password)


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """验证密码的便捷函数"""
    return security_manager.verify_password(password, password_hash, salt)


def generate_secure_token(length: int = 32) -> str:
    """生成安全令牌的便捷函数"""
    return security_manager.generate_secure_token(length)


def mask_sensitive_data(data: str, show_chars: int = 4) -> str:
    """掩码敏感数据的便捷函数"""
    return security_manager.mask_sensitive_data(data, show_chars)