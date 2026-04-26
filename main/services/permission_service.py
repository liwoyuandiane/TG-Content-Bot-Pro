"""权限管理服务"""
import logging
from typing import List, Optional
from ..config import settings
from .user_service import user_service

logger = logging.getLogger(__name__)


class PermissionService:
    """权限管理服务"""
    
    def __init__(self):
        self._owner_ids = None
    
    def _get_owner_ids(self) -> List[int]:
        """获取所有者ID列表"""
        if self._owner_ids is None:
            # 从环境变量获取所有者ID，支持多个所有者（逗号分隔）
            auth_var = settings.AUTH
            if isinstance(auth_var, int):
                self._owner_ids = [auth_var]
            elif isinstance(auth_var, str):
                try:
                    # 尝试解析逗号分隔的ID列表
                    self._owner_ids = [int(id_str.strip()) for id_str in auth_var.split(',')]
                except ValueError:
                    # 如果解析失败，退回到单个ID
                    self._owner_ids = [int(auth_var)]
            else:
                self._owner_ids = []
        return self._owner_ids
    
    async def is_owner(self, user_id: int) -> bool:
        """检查用户是否为所有者"""
        return user_id in self._get_owner_ids()
    
    async def is_user_authorized(self, user_id: int) -> bool:
        """检查用户是否被授权"""
        # 所有者自动获得授权
        if await self.is_owner(user_id):
            return True
        
        # 检查数据库中的授权状态
        return await user_service.is_user_authorized(user_id)
    
    async def require_owner(self, user_id: int) -> bool:
        """要求用户必须是所有者，否则返回False"""
        return await self.is_owner(user_id)
    
    async def require_authorized(self, user_id: int) -> bool:
        """要求用户必须被授权，否则返回False"""
        return await self.is_user_authorized(user_id)
    
    async def get_permission_level(self, user_id: int) -> str:
        """获取用户的权限级别"""
        if await self.is_owner(user_id):
            return "owner"
        elif await user_service.is_user_authorized(user_id):
            return "authorized"
        else:
            return "unauthorized"


# 全局权限服务实例
permission_service = PermissionService()