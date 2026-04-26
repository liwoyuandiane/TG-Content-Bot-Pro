"""用户等级服务模块

该模块提供用户等级管理功能，包括检查用户等级、获取批量限制等。
"""
import logging
from ..core.database import db_manager
from ..config import settings

logger = logging.getLogger(__name__)


class TierService:
    """用户等级服务
    
    负责管理用户等级和批量处理限制。
    """
    
    def __init__(self):
        self.db = db_manager
    
    def is_super_admin(self, user_id: int) -> bool:
        """检查用户是否为超级管理员（AUTH用户）
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 用户是否为超级管理员
        """
        return user_id in settings.get_auth_users()
    
    async def is_premium_user(self, user_id: int) -> bool:
        """检查用户是否为Premium
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 用户是否为Premium
        """
        # 超级管理员自动是Premium
        if self.is_super_admin(user_id):
            return True
        return await self.db.is_user_premium(user_id)
    
    async def get_batch_limit(self, user_id: int) -> int:
        """获取用户的批量处理限制
        
        Args:
            user_id: 用户ID
            
        Returns:
            int: 用户允许的批量处理最大数量
        """
        # 超级管理员无限制
        if self.is_super_admin(user_id):
            return 999999
        if await self.is_premium_user(user_id):
            return settings.PREMIUM_LIMIT
        return settings.FREEMIUM_LIMIT
    
    async def set_user_premium(self, user_id: int, is_premium: bool) -> bool:
        """设置用户等级
        
        Args:
            user_id: 用户ID
            is_premium: 是否为Premium
            
        Returns:
            bool: 操作是否成功
        """
        return await self.db.set_user_premium(user_id, is_premium)
    
    async def upgrade_user(self, user_id: int) -> bool:
        """提升用户为Premium
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 操作是否成功
        """
        logger.info(f"提升用户 {user_id} 为Premium")
        return await self.set_user_premium(user_id, True)
    
    async def downgrade_user(self, user_id: int) -> bool:
        """降级用户为普通用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 操作是否成功
        """
        logger.info(f"降级用户 {user_id} 为普通用户")
        return await self.set_user_premium(user_id, False)
    
    def get_tier_name(self, user_id: int) -> str:
        """获取用户等级名称
        
        Args:
            user_id: 用户ID
            
        Returns:
            str: 用户等级名称
        """
        return "Premium" if settings.PREMIUM_LIMIT > 0 else "普通用户"
    
    def get_tier_info(self, user_id: int) -> dict:
        """获取用户等级信息
        
        Returns:
            dict: 包含用户等级和限制信息的字典
        """
        return {
            "freemium_limit": settings.FREEMIUM_LIMIT,
            "premium_limit": settings.PREMIUM_LIMIT
        }


# 全局用户等级服务实例
tier_service = TierService()
