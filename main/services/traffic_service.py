"""流量服务模块"""
import logging
from typing import Optional, Dict, Any, Tuple
from ..core.database import db_manager

logger = logging.getLogger(__name__)


class TrafficService:
    """流量管理服务"""
    
    def __init__(self):
        self.db = db_manager
    
    async def add_traffic(self, user_id: int, upload_bytes: int = 0, download_bytes: int = 0) -> bool:
        """添加流量统计"""
        return await self.db.add_traffic(user_id, upload_bytes, download_bytes)
    
    async def get_user_traffic(self, user_id: int) -> Optional[Dict[str, int]]:
        """获取用户流量统计"""
        return await self.db.get_user_traffic(user_id)
    
    async def get_total_traffic(self) -> Optional[Dict[str, int]]:
        """获取总流量统计"""
        return await self.db.get_total_traffic()
    
    async def get_traffic_limits(self) -> Optional[Dict[str, Any]]:
        """获取流量限制配置"""
        return await self.db.get_traffic_limits()
    
    async def update_traffic_limits(self, daily_limit: Optional[int] = None,
                                  monthly_limit: Optional[int] = None,
                                  per_file_limit: Optional[int] = None,
                                  enabled: Optional[int] = None) -> bool:
        """更新流量限制配置"""
        return await self.db.update_traffic_limits(daily_limit, monthly_limit, per_file_limit, enabled)
    
    async def check_traffic_limit(self, user_id: int, file_size: int) -> Tuple[bool, Optional[str]]:
        """检查流量限制"""
        return await self.db.check_traffic_limit(user_id, file_size)
    
    @staticmethod
    def format_bytes(bytes_num: int) -> str:
        """格式化字节数"""
        return db_manager.format_bytes(bytes_num)


# 全局流量服务实例
traffic_service = TrafficService()