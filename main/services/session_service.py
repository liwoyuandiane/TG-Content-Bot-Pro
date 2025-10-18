"""会话服务模块"""
import logging
import hashlib
import secrets
from typing import Optional, List, Dict, Any
from datetime import datetime
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from ..core.database import db_manager
from ..config import settings
from ..exceptions.telegram import SessionException

logger = logging.getLogger(__name__)


class SessionService:
    """会话管理服务"""
    
    def __init__(self):
        self.db = db_manager
        self.cipher_suite = None
        self._init_encryption()
    
    def _init_encryption(self):
        """初始化加密系统"""
        try:
            if settings.ENCRYPTION_KEY:
                # 使用提供的密钥
                key = settings.ENCRYPTION_KEY.encode()
                if len(key) != 32:
                    # 如果不是32字节，使用PBKDF2派生密钥
                    salt = b'tg_content_bot_salt_16bytes'  # 固定盐值
                    kdf = PBKDF2HMAC(
                        algorithm=hashes.SHA256(),
                        length=32,
                        salt=salt,
                        iterations=100000,
                    )
                    key = base64.urlsafe_b64encode(kdf.derive(key))
                self.cipher_suite = Fernet(key)
                logger.info("会话加密已启用")
            else:
                logger.warning("会话加密未配置，SESSION将明文存储")
        except Exception as e:
            logger.error(f"初始化加密系统失败: {e}")
            self.cipher_suite = None
    
    def _generate_encryption_key(self) -> str:
        """生成新的加密密钥"""
        return Fernet.generate_key().decode()
    
    def _encrypt_session(self, session_string: str) -> Optional[str]:
        """加密SESSION字符串"""
        if not self.cipher_suite:
            return session_string  # 未启用加密时直接返回
        
        try:
            encrypted_session = self.cipher_suite.encrypt(session_string.encode())
            return encrypted_session.decode()
        except Exception as e:
            logger.error(f"加密SESSION失败: {e}")
            return None
    
    def _decrypt_session(self, encrypted_session: str) -> Optional[str]:
        """解密SESSION字符串"""
        if not self.cipher_suite:
            return encrypted_session  # 未启用加密时直接返回
        
        try:
            decrypted_session = self.cipher_suite.decrypt(encrypted_session.encode())
            return decrypted_session.decode()
        except InvalidToken:
            logger.error("SESSION解密失败：无效令牌")
            return None
        except Exception as e:
            logger.error(f"解密SESSION失败: {e}")
            return None
    
    async def save_session(self, user_id: int, session_string: str, session_name: str = "default") -> bool:
        """保存SESSION字符串"""
        if not session_string:
            logger.warning("尝试保存空的SESSION字符串")
            return False
        
        # 验证SESSION格式
        if not self._validate_session_format(session_string):
            logger.warning("SESSION格式无效")
            return False
        
        # 加密SESSION
        encrypted_session = self._encrypt_session(session_string)
        if encrypted_session is None:
            return False
        
        try:
            # 保存到数据库
            result = await self.db.save_session(user_id, encrypted_session)
            if result:
                logger.info(f"SESSION已保存: 用户 {user_id}")
            else:
                logger.error(f"保存SESSION失败: 用户 {user_id}")
            return result
        except Exception as e:
            logger.error(f"保存SESSION时数据库错误: {e}")
            return False
    
    async def get_session(self, user_id: int) -> Optional[str]:
        """获取SESSION字符串"""
        try:
            encrypted_session = await self.db.get_session(user_id)
            if not encrypted_session:
                logger.debug(f"用户 {user_id} 未找到SESSION")
                return None
            
            # 解密SESSION
            session_string = self._decrypt_session(encrypted_session)
            if session_string is None:
                logger.error(f"解密用户 {user_id} 的SESSION失败")
                return None
            
            return session_string
        except Exception as e:
            logger.error(f"获取SESSION时数据库错误: {e}")
            return None
    
    async def delete_session(self, user_id: int) -> bool:
        """删除SESSION字符串"""
        try:
            result = await self.db.delete_session(user_id)
            if result:
                logger.info(f"SESSION已删除: 用户 {user_id}")
            else:
                logger.warning(f"删除SESSION失败: 用户 {user_id} 未找到SESSION")
            return result
        except Exception as e:
            logger.error(f"删除SESSION时数据库错误: {e}")
            return False
    
    async def get_all_sessions(self) -> List[Dict[str, Any]]:
        """获取所有SESSION"""
        try:
            sessions = await self.db.get_all_sessions()
            
            # 解密所有SESSION
            for session in sessions:
                if session.get("session_string"):
                    decrypted_session = self._decrypt_session(session["session_string"])
                    session["session_string"] = decrypted_session
            
            return sessions
        except Exception as e:
            logger.error(f"获取所有SESSION时数据库错误: {e}")
            return []
    
    async def update_session(self, user_id: int, session_string: str) -> bool:
        """更新SESSION字符串"""
        return await self.save_session(user_id, session_string)
    
    async def session_exists(self, user_id: int) -> bool:
        """检查SESSION是否存在"""
        try:
            session = await self.db.get_session(user_id)
            return session is not None
        except Exception as e:
            logger.error(f"检查SESSION存在性时数据库错误: {e}")
            return False
    
    def _validate_session_format(self, session_string: str) -> bool:
        """验证SESSION格式"""
        # 基本格式检查
        if not session_string or len(session_string) < 10:
            return False
        
        # 检查是否包含必要的组件
        # Pyrogram session strings are typically base64 encoded
        try:
            # 尝试base64解码来验证格式
            import base64
            base64.b64decode(session_string)
            return True
        except Exception:
            return False
    
    async def validate_session(self, user_id: int, session_string: str) -> bool:
        """验证SESSION有效性"""
        # 这里可以实现更复杂的SESSION验证逻辑
        # 例如，尝试创建一个临时客户端来验证SESSION
        return self._validate_session_format(session_string)
    
    def generate_session_hash(self, session_string: str) -> str:
        """生成SESSION哈希用于安全比较"""
        return hashlib.sha256(session_string.encode()).hexdigest()
    
    async def get_session_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取SESSION信息（不包含实际SESSION字符串）"""
        try:
            user = await self.db.get_user(user_id)
            if not user:
                return None
            
            return {
                "user_id": user_id,
                "has_session": user.get("session_string") is not None,
                "session_updated": user.get("session_updated"),
                "is_encrypted": self.cipher_suite is not None
            }
        except Exception as e:
            logger.error(f"获取SESSION信息时数据库错误: {e}")
            return None


# 全局会话服务实例
session_service = SessionService()