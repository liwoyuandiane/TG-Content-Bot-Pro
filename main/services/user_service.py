"""用户服务模块"""
import logging
from typing import Optional, Dict, Any
from ..core.database import db_manager

logger = logging.getLogger(__name__)


class UserService:
    """用户管理服务"""
    
    def __init__(self):
        self.db = db_manager
    
    async def add_user(self, user_id: int, username: Optional[str] = None,
                      first_name: Optional[str] = None, last_name: Optional[str] = None) -> bool:
        """添加或更新用户"""
        return await self.db.add_user(user_id, username, first_name, last_name)
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        return await self.db.get_user(user_id)
    
    async def is_user_banned(self, user_id: int) -> bool:
        """检查用户是否被封禁"""
        return await self.db.is_user_banned(user_id)
    
    async def ban_user(self, user_id: int) -> bool:
        """封禁用户"""
        return await self.db.ban_user(user_id)
    
    async def unban_user(self, user_id: int) -> bool:
        """解封用户"""
        return await self.db.unban_user(user_id)
    
    async def get_all_users_count(self) -> int:
        """获取总用户数"""
        return await self.db.get_all_users_count()
    
    async def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户统计信息"""
        return await self.db.get_user_stats(user_id)


# 全局用户服务实例
user_service = UserService()