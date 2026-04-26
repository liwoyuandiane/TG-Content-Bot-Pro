"""数据库管理模块

该模块提供MongoDB数据库的连接管理和数据操作功能，
包括用户管理、消息记录、流量统计等核心数据的存储和查询。
"""
import asyncio
import logging
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, date

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError, ServerSelectionTimeoutError
from bson.objectid import ObjectId

from ..config import settings
from ..exceptions.base import BaseBotException

logger = logging.getLogger(__name__)


class DatabaseConnectionError(BaseBotException):
    """数据库连接异常
    
    当数据库连接失败时抛出此异常。
    
    Attributes:
        message: 错误信息
        error_code: 错误代码 "DATABASE_CONNECTION_ERROR"
    """
    def __init__(self, message: str) -> None:
        """初始化数据库连接异常
        
        Args:
            message: 错误信息
        """
        super().__init__(message, "DATABASE_CONNECTION_ERROR")


class DatabaseOperationError(BaseBotException):
    """数据库操作异常
    
    当数据库操作失败时抛出此异常。
    
    Attributes:
        message: 错误信息
        error_code: 错误代码 "DATABASE_OPERATION_ERROR"
    """
    def __init__(self, message: str) -> None:
        """初始化数据库操作异常
        
        Args:
            message: 错误信息
        """
        super().__init__(message, "DATABASE_OPERATION_ERROR")


class DatabaseManager:
    """MongoDB数据库管理器
    
    负责MongoDB数据库的连接管理、数据操作和连接池管理。
    提供用户管理、消息记录、流量统计等核心功能。
    """
    
    def __init__(self) -> None:
        """初始化数据库管理器"""
        self.client: Optional[MongoClient] = None
        self.db = None
        self._lock = asyncio.Lock()
        self._last_health_check = None
        self._connection_errors = 0
        self._max_connection_errors = 3
        self._connect()
    
    def _connect(self) -> None:
        """连接到MongoDB数据库
        
        建立MongoDB连接并初始化数据库和索引。
        
        Raises:
            DatabaseConnectionError: 当连接失败时
        """
        if not settings.MONGO_DB:
            logger.warning("未配置MongoDB连接字符串")
            return
        
        try:
            logger.info("正在连接MongoDB...")
            # 优化连接池配置
            pool_config = {
                'serverSelectionTimeoutMS': 10000,  # 增加到10秒
                'connectTimeoutMS': 10000,          # 增加到10秒
                'socketTimeoutMS': 30000,          # 增加到30秒
                'maxPoolSize': 20,                  # 增大连接池
                'minPoolSize': 5,                   # 最小连接数
                'maxIdleTimeMS': 60000,             # 空闲连接超时
                'waitQueueTimeoutMS': 10000,        # 等待队列超时
                'retryWrites': True,               # 启用重试写入
                'retryReads': True,                # 启用重试读取
                'connect': False                   # 延迟连接
            }
            
            self.client = MongoClient(settings.MONGO_DB, **pool_config)
            # 测试连接
            self.client.admin.command('ping')
            self.db = self.client['tg_content_bot']
            logger.info("MongoDB数据库连接成功")
            
            # 创建索引
            self._create_indexes()
            
        except ConfigurationError as e:
            logger.error(f"MongoDB配置错误: {e}")
            raise DatabaseConnectionError(f"MongoDB配置错误: {e}")
        except ServerSelectionTimeoutError as e:
            logger.error(f"MongoDB连接超时: {e}")
            raise DatabaseConnectionError(f"MongoDB连接超时: {e}")
        except ConnectionFailure as e:
            logger.error(f"MongoDB连接失败: {e}")
            raise DatabaseConnectionError(f"MongoDB连接失败: {e}")
        except Exception as e:
            logger.error(f"MongoDB未知错误: {e}")
            raise DatabaseConnectionError(f"MongoDB未知错误: {e}")
    
    def _create_indexes(self) -> None:
        """创建数据库索引
        
        为常用查询字段创建索引以提高查询性能。
        """
        try:
            if self.db is None:
                return
                
            # 用户索引
            self.db.users.create_index("user_id", unique=True)
            self.db.users.create_index("is_premium")
            
            # 消息历史索引
            self.db.message_history.create_index([("user_id", 1), ("forward_date", -1)])
            
            # 批量任务索引
            self.db.batch_tasks.create_index([("user_id", 1), ("start_time", -1)])
            
            # 流量统计索引
            self.db.users.create_index("last_reset_daily")
            self.db.users.create_index("last_reset_monthly")
            
            logger.info("数据库索引创建完成")
        except Exception as e:
            logger.warning(f"创建索引失败: {e}")
    
    def _ensure_connection(self) -> None:
        """确保数据库连接有效
        
        检查数据库连接状态，如果连接失效则重新连接。
        实现智能重试和错误计数机制。
        """
        if not self.client:
            self._connect()
            return
        
        try:
            # 检查连接是否仍然有效
            self.client.admin.command('ping')
            self._connection_errors = 0  # 重置错误计数
            self._last_health_check = datetime.now()
        except Exception as e:
            self._connection_errors += 1
            logger.warning(f"数据库连接失效 ({self._connection_errors}/{self._max_connection_errors}): {e}")
            
            if self._connection_errors >= self._max_connection_errors:
                logger.error("数据库连接错误次数过多，尝试重新连接")
                self._connect()
            else:
                # 如果是偶发性错误，不立即重新连接
                logger.warning("数据库连接暂时性错误，继续使用现有连接")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取数据库连接统计信息"""
        if not self.client:
            return {"status": "disconnected", "pool_size": 0, "connection_errors": self._connection_errors}
        
        try:
            # 获取连接池信息
            server_status = self.client.admin.command('serverStatus')
            connections = server_status.get('connections', {})
            
            return {
                "status": "connected",
                "pool_size": connections.get('current', 0),
                "connection_errors": self._connection_errors,
                "last_health_check": self._last_health_check
            }
        except Exception:
            return {"status": "error", "connection_errors": self._connection_errors}
    
    def is_connected(self) -> bool:
        """检查数据库是否连接
        
        Returns:
            bool: 数据库是否连接成功
        """
        if not self.client or self.db is None:
            return False
        
        try:
            self.client.admin.command('ping')
            return True
        except Exception:
            return False
    
    # ==================== 用户管理 ====================
    
    async def add_user(self, user_id: int, username: Optional[str] = None, 
                      first_name: Optional[str] = None, last_name: Optional[str] = None,
                      is_authorized: bool = False) -> bool:
        """添加或更新用户
        
        Args:
            user_id: 用户ID
            username: 用户名
            first_name: 名字
            last_name: 姓氏
            is_authorized: 是否为授权用户
            
        Returns:
            bool: 操作是否成功
        """
        async with self._lock:
            if self.db is None:
                return False
            
            try:
                self._ensure_connection()
                now = datetime.now()
                result = self.db.users.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {
                            "username": username,
                            "first_name": first_name,
                            "last_name": last_name,
                            "last_used": now
                        },
                        "$setOnInsert": {
                            "join_date": now,
                            "is_banned": False,
                            "is_authorized": is_authorized,  # 添加授权字段
                            "is_premium": False,  # 用户等级：False=普通用户, True=Premium用户
                            "total_forwards": 0,
                            "total_size": 0,
                            "last_forward": None,
                            "daily_upload": 0,
                            "daily_download": 0,
                            "monthly_upload": 0,
                            "monthly_download": 0,
                            "total_upload": 0,
                            "total_download": 0,
                            "last_reset_daily": now.date().isoformat(),
                            "last_reset_monthly": now.strftime("%Y-%m")
                        }
                    },
                    upsert=True
                )
                return True
            except Exception as e:
                logger.error(f"添加用户失败: {e}")
                return False
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[Dict[str, Any]]: 用户信息字典，如果用户不存在则返回None
        """
        async with self._lock:
            if self.db is None:
                return None
            
            try:
                self._ensure_connection()
                return self.db.users.find_one({"user_id": user_id})
            except Exception as e:
                logger.error(f"获取用户失败: {e}")
                return None
    
    async def is_user_banned(self, user_id: int) -> bool:
        """检查用户是否被封禁
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 用户是否被封禁
        """
        user = await self.get_user(user_id)
        return user and user.get('is_banned', False)
    
    async def is_user_premium(self, user_id: int) -> bool:
        """检查用户是否为Premium
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 用户是否为Premium
        """
        user = await self.get_user(user_id)
        return user and user.get('is_premium', False)
    
    async def set_user_premium(self, user_id: int, is_premium: bool) -> bool:
        """设置用户等级
        
        Args:
            user_id: 用户ID
            is_premium: 是否为Premium
            
        Returns:
            bool: 操作是否成功
        """
        async with self._lock:
            if self.db is None:
                return False
            
            try:
                self._ensure_connection()
                result = self.db.users.update_one(
                    {"user_id": user_id},
                    {"$set": {"is_premium": is_premium}}
                )
                return result.modified_count > 0
            except Exception as e:
                logger.error(f"设置用户等级失败: {e}")
                return False
    
    async def ban_user(self, user_id: int) -> bool:
        """封禁用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 操作是否成功
        """
        async with self._lock:
            if self.db is None:
                return False
            
            try:
                self._ensure_connection()
                result = self.db.users.update_one(
                    {"user_id": user_id},
                    {"$set": {"is_banned": True}}
                )
                return result.modified_count > 0
            except Exception as e:
                logger.error(f"封禁用户失败: {e}")
                return False
    
    async def unban_user(self, user_id: int) -> bool:
        """解封用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 操作是否成功
        """
        async with self._lock:
            if self.db is None:
                return False
            
            try:
                self._ensure_connection()
                result = self.db.users.update_one(
                    {"user_id": user_id},
                    {"$set": {"is_banned": False}}
                )
                return result.modified_count > 0
            except Exception as e:
                logger.error(f"解封用户失败: {e}")
                return False
    
    async def get_all_users_count(self) -> int:
        """获取总用户数
        
        Returns:
            int: 总用户数
        """
        async with self._lock:
            if self.db is None:
                return 0
            
            try:
                self._ensure_connection()
                return self.db.users.count_documents({})
            except Exception as e:
                logger.error(f"获取用户数失败: {e}")
                return 0
    
    # ==================== 消息管理 ====================
    
    async def add_forward(self, user_id: int, message_link: str, message_id: int, 
                         chat_id: str, media_type: str, file_size: int = 0, status: str = "success") -> bool:
        """添加转发记录
        
        Args:
            user_id: 用户ID
            message_link: 消息链接
            message_id: 消息ID
            chat_id: 聊天ID
            media_type: 媒体类型
            file_size: 文件大小（字节）
            status: 转发状态
            
        Returns:
            bool: 操作是否成功
        """
        async with self._lock:
            if self.db is None:
                return False
            
            try:
                self._ensure_connection()
                now = datetime.now()
                
                # 添加转发历史
                self.db.message_history.insert_one({
                    "user_id": user_id,
                    "message_link": message_link,
                    "message_id": message_id,
                    "chat_id": chat_id,
                    "media_type": media_type,
                    "file_size": file_size,
                    "forward_date": now,
                    "status": status
                })
                
                # 更新用户统计（仅在成功时）
                if status == "success":
                    self.db.users.update_one(
                        {"user_id": user_id},
                        {
                            "$inc": {
                                "total_forwards": 1,
                                "total_size": file_size
                            },
                            "$set": {
                                "last_forward": now
                            }
                        }
                    )
                
                return True
            except Exception as e:
                logger.error(f"添加转发记录失败: {e}")
                return False
    
    async def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户统计信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[Dict[str, Any]]: 用户统计信息，如果用户不存在则返回None
        """
        async with self._lock:
            if self.db is None:
                return None
            
            try:
                self._ensure_connection()
                user = self.db.users.find_one({"user_id": user_id})
                if not user:
                    return None
                
                return {
                    "total_forwards": user.get("total_forwards", 0),
                    "total_size": user.get("total_size", 0),
                    "last_forward": user.get("last_forward")
                }
            except Exception as e:
                logger.error(f"获取用户统计失败: {e}")
                return None
    
    async def get_authorized_users(self) -> List[int]:
        """获取所有授权用户ID列表
        
        Returns:
            List[int]: 授权用户ID列表
        """
        async with self._lock:
            if self.db is None:
                return []
            
            try:
                self._ensure_connection()
                users = list(self.db.users.find({"is_authorized": True}, {"user_id": 1}))
                return [user["user_id"] for user in users]
            except Exception as e:
                logger.error(f"获取授权用户列表失败: {e}")
                return []
    
    async def authorize_user(self, user_id: int) -> bool:
        """授权用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 操作是否成功
        """
        async with self._lock:
            if self.db is None:
                return False
            
            try:
                self._ensure_connection()
                result = self.db.users.update_one(
                    {"user_id": user_id},
                    {"$set": {"is_authorized": True}}
                )
                return result.modified_count > 0
            except Exception as e:
                logger.error(f"授权用户失败: {e}")
                return False
    
    async def unauthorize_user(self, user_id: int) -> bool:
        """取消用户授权
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 操作是否成功
        """
        async with self._lock:
            if self.db is None:
                return False
            
            try:
                self._ensure_connection()
                # 不能取消主用户的授权
                from ..config import settings
                if user_id in settings.get_auth_users():
                    return False
                
                result = self.db.users.update_one(
                    {"user_id": user_id},
                    {"$set": {"is_authorized": False}}
                )
                return result.modified_count > 0
            except Exception as e:
                logger.error(f"取消用户授权失败: {e}")
                return False
    
    async def is_user_authorized(self, user_id: int) -> bool:
        """检查用户是否被授权
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 用户是否被授权
        """
        # 首先检查是否为主用户
        from ..config import settings
        if user_id in settings.get_auth_users():
            return True
        
        # 然后检查数据库中的授权状态
        user = await self.get_user(user_id)
        return user and user.get('is_authorized', False)
    
    async def get_forward_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """获取用户转发历史
        
        Args:
            user_id: 用户ID
            limit: 返回记录数量限制
            
        Returns:
            List[Dict[str, Any]]: 转发历史记录列表
        """
        async with self._lock:
            if self.db is None:
                return []
            
            try:
                self._ensure_connection()
                history = list(
                    self.db.message_history.find({"user_id": user_id})
                    .sort("forward_date", -1)
                    .limit(limit)
                )
                
                return [{
                    "message_link": h.get("message_link"),
                    "media_type": h.get("media_type"),
                    "file_size": h.get("file_size", 0),
                    "forward_date": h.get("forward_date").isoformat() if h.get("forward_date") else "",
                    "status": h.get("status")
                } for h in history]
            except Exception as e:
                logger.error(f"获取转发历史失败: {e}")
                return []
    
    async def get_recent_forward_history(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """获取所有用户最近的转发历史
        
        Args:
            limit: 返回记录数量限制
            offset: 偏移量，用于分页
            
        Returns:
            List[Dict[str, Any]]: 转发历史记录列表
        """
        async with self._lock:
            if self.db is None:
                return []
            
            try:
                self._ensure_connection()
                cursor = self.db.message_history.find({}).sort("forward_date", -1).skip(offset).limit(limit)
                history = list(cursor)
                
                # 安全地序列化所有字段，处理MongoDB特殊对象类型
                result = []
                for h in history:
                    # 处理ObjectId和其他MongoDB特殊类型
                    record = {}
                    for key, value in h.items():
                        try:
                            # 更安全地检查MongoDB ObjectId
                            if hasattr(value, '__class__') and 'bson.objectid.ObjectId' in str(type(value)):
                                record[key] = str(value)
                            # 更安全地检查是否有isoformat方法（datetime对象）
                            elif hasattr(value, 'isoformat') and callable(getattr(value, 'isoformat', None)):
                                record[key] = value.isoformat()
                            else:
                                record[key] = value
                        except Exception as e:
                            logger.error(f"处理字段 {key} 时出错: {e}")
                            # 如果有任何问题，直接使用原始值
                            record[key] = value
                    
                    # 确保特定字段的类型安全转换
                    if "message_link" in record and record["message_link"] is not None:
                        record["message_link"] = str(record["message_link"])
                    if "media_type" in record and record["media_type"] is not None:
                        record["media_type"] = str(record["media_type"])
                    if "file_size" in record and record["file_size"] is not None:
                        try:
                            record["file_size"] = int(record["file_size"])
                        except (ValueError, TypeError):
                            record["file_size"] = 0
                    if "status" in record and record["status"] is not None:
                        record["status"] = str(record["status"])
                    if "user_id" in record and record["user_id"] is not None:
                        try:
                            record["user_id"] = int(record["user_id"])
                        except (ValueError, TypeError):
                            record["user_id"] = None
                    
                    result.append(record)
                
                return result
            except Exception as e:
                logger.error(f"获取最近转发历史失败: {e}")
                import traceback
                logger.error(f"详细错误信息: {traceback.format_exc()}")
                return []
    
    async def get_total_forwards(self) -> int:
        """获取总转发数
        
        Returns:
            int: 总转发数
        """
        async with self._lock:
            if self.db is None:
                return 0
            
            try:
                self._ensure_connection()
                result = self.db.users.aggregate([
                    {"$group": {"_id": None, "total": {"$sum": "$total_forwards"}}}
                ])
                data = list(result)
                return data[0]["total"] if data else 0
            except Exception as e:
                logger.error(f"获取总转发数失败: {e}")
                return 0
    
    # ==================== 批量任务管理 ====================
    
    async def create_batch_task(self, user_id: int, start_link: str, message_count: int) -> Optional[str]:
        """创建批量任务
        
        Args:
            user_id: 用户ID
            start_link: 起始消息链接
            message_count: 消息数量
            
        Returns:
            Optional[str]: 任务ID，如果创建失败则返回None
        """
        async with self._lock:
            if self.db is None:
                return None
            
            try:
                self._ensure_connection()
                now = datetime.now()
                result = self.db.batch_tasks.insert_one({
                    "user_id": user_id,
                    "start_link": start_link,
                    "message_count": message_count,
                    "completed_count": 0,
                    "status": "running",
                    "start_time": now,
                    "end_time": None
                })
                return str(result.inserted_id)
            except Exception as e:
                logger.error(f"创建批量任务失败: {e}")
                return None
    
    async def update_batch_progress(self, task_id: str, completed_count: int) -> bool:
        """更新批量任务进度
        
        Args:
            task_id: 任务ID
            completed_count: 已完成数量
            
        Returns:
            bool: 操作是否成功
        """
        async with self._lock:
            if not self.db or not task_id:
                return False
            
            try:
                self._ensure_connection()
                result = self.db.batch_tasks.update_one(
                    {"_id": ObjectId(task_id)},
                    {"$set": {"completed_count": completed_count}}
                )
                return result.modified_count > 0
            except Exception as e:
                logger.error(f"更新批量任务进度失败: {e}")
                return False
    
    async def complete_batch_task(self, task_id: str) -> bool:
        """完成批量任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 操作是否成功
        """
        async with self._lock:
            if not self.db or not task_id:
                return False
            
            try:
                self._ensure_connection()
                result = self.db.batch_tasks.update_one(
                    {"_id": ObjectId(task_id)},
                    {
                        "$set": {
                            "status": "completed",
                            "end_time": datetime.now()
                        }
                    }
                )
                return result.modified_count > 0
            except Exception as e:
                logger.error(f"完成批量任务失败: {e}")
                return False
    
    async def cancel_batch_task(self, task_id: str) -> bool:
        """取消批量任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 操作是否成功
        """
        async with self._lock:
            if not self.db or not task_id:
                return False
            
            try:
                self._ensure_connection()
                result = self.db.batch_tasks.update_one(
                    {"_id": ObjectId(task_id)},
                    {
                        "$set": {
                            "status": "cancelled",
                            "end_time": datetime.now()
                        }
                    }
                )
                return result.modified_count > 0
            except Exception as e:
                logger.error(f"取消批量任务失败: {e}")
                return False
    
    # ==================== 流量管理 ====================
    
    async def add_traffic(self, user_id: int, upload_bytes: int = 0, download_bytes: int = 0) -> bool:
        """添加流量统计
        
        Args:
            user_id: 用户ID
            upload_bytes: 上传字节数
            download_bytes: 下载字节数
            
        Returns:
            bool: 操作是否成功
        """
        async with self._lock:
            if not self.db or upload_bytes < 0 or download_bytes < 0:
                return False
            
            try:
                self._ensure_connection()
                now = datetime.now()
                today = now.date().isoformat()
                month = now.strftime("%Y-%m")
                
                # 更新流量统计
                result = self.db.users.update_one(
                    {"user_id": user_id},
                    {
                        "$inc": {
                            "daily_upload": upload_bytes,
                            "daily_download": download_bytes,
                            "monthly_upload": upload_bytes,
                            "monthly_download": download_bytes,
                            "total_upload": upload_bytes,
                            "total_download": download_bytes
                        },
                        "$set": {
                            "last_reset_daily": today,
                            "last_reset_monthly": month
                        }
                    }
                )
                
                return result.modified_count > 0
            except Exception as e:
                logger.error(f"添加流量统计失败: {e}")
                return False
    
    async def get_user_traffic(self, user_id: int) -> Optional[Dict[str, int]]:
        """获取用户流量统计
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[Dict[str, int]]: 用户流量统计，如果用户不存在则返回None
        """
        async with self._lock:
            if self.db is None:
                return None
            
            try:
                self._ensure_connection()
                user = self.db.users.find_one({"user_id": user_id})
                if not user:
                    return None
                
                return {
                    "daily_upload": user.get("daily_upload", 0),
                    "daily_download": user.get("daily_download", 0),
                    "monthly_upload": user.get("monthly_upload", 0),
                    "monthly_download": user.get("monthly_download", 0),
                    "total_upload": user.get("total_upload", 0),
                    "total_download": user.get("total_download", 0)
                }
            except Exception as e:
                logger.error(f"获取用户流量失败: {e}")
                return None
    
    async def get_total_traffic(self) -> Optional[Dict[str, int]]:
        """获取总流量统计
        
        Returns:
            Optional[Dict[str, int]]: 总流量统计
        """
        async with self._lock:
            if self.db is None:
                return None
            
            try:
                self._ensure_connection()
                # 今日总流量
                today = date.today().isoformat()
                today_result = self.db.users.aggregate([
                    {"$match": {"last_reset_daily": today}},
                    {
                        "$group": {
                            "_id": None,
                            "download": {"$sum": "$daily_download"}
                        }
                    }
                ])
                today_data = list(today_result)
                
                # 本月总流量
                month = datetime.now().strftime("%Y-%m")
                month_result = self.db.users.aggregate([
                    {"$match": {"last_reset_monthly": month}},
                    {
                        "$group": {
                            "_id": None,
                            "download": {"$sum": "$monthly_download"}
                        }
                    }
                ])
                month_data = list(month_result)
                
                # 累计总流量
                total_result = self.db.users.aggregate([
                    {
                        "$group": {
                            "_id": None,
                            "upload": {"$sum": "$total_upload"},
                            "download": {"$sum": "$total_download"}
                        }
                    }
                ])
                total_data = list(total_result)
                
                return {
                    "today_download": today_data[0]["download"] if today_data else 0,
                    "month_download": month_data[0]["download"] if month_data else 0,
                    "total_upload": total_data[0]["upload"] if total_data else 0,
                    "total_download": total_data[0]["download"] if total_data else 0
                }
            except Exception as e:
                logger.error(f"获取总流量失败: {e}")
                return None
    
    async def get_traffic_limits(self) -> Optional[Dict[str, Any]]:
        """获取流量限制配置
        
        Returns:
            Optional[Dict[str, Any]]: 流量限制配置
        """
        async with self._lock:
            if self.db is None:
                return None
            
            try:
                self._ensure_connection()
                limits = self.db.settings.find_one({"type": "traffic_limits"})
                if not limits:
                    # 创建默认配置
                    default_limits = {
                        "type": "traffic_limits",
                        "daily_limit": settings.DEFAULT_DAILY_LIMIT,
                        "monthly_limit": settings.DEFAULT_MONTHLY_LIMIT,
                        "per_file_limit": settings.DEFAULT_PER_FILE_LIMIT,
                        "enabled": 1
                    }
                    self.db.settings.insert_one(default_limits)
                    return default_limits
                return limits
            except Exception as e:
                logger.error(f"获取流量限制失败: {e}")
                return None
    
    async def update_traffic_limits(self, daily_limit: Optional[int] = None, 
                                   monthly_limit: Optional[int] = None, 
                                   per_file_limit: Optional[int] = None, 
                                   enabled: Optional[int] = None) -> bool:
        """更新流量限制配置
        
        Args:
            daily_limit: 每日限制（字节）
            monthly_limit: 每月限制（字节）
            per_file_limit: 单文件限制（字节）
            enabled: 是否启用
            
        Returns:
            bool: 操作是否成功
        """
        async with self._lock:
            if self.db is None:
                return False
            
            try:
                self._ensure_connection()
                update_data = {}
                if daily_limit is not None:
                    update_data["daily_limit"] = daily_limit
                if monthly_limit is not None:
                    update_data["monthly_limit"] = monthly_limit
                if per_file_limit is not None:
                    update_data["per_file_limit"] = per_file_limit
                if enabled is not None:
                    update_data["enabled"] = enabled
                
                if update_data:
                    self.db.settings.update_one(
                        {"type": "traffic_limits"},
                        {"$set": update_data},
                        upsert=True
                    )
                return True
            except Exception as e:
                logger.error(f"更新流量限制失败: {e}")
                return False
    
    async def check_traffic_limit(self, user_id: int, file_size: int) -> tuple[bool, Optional[str]]:
        """检查流量限制
        
        Args:
            user_id: 用户ID
            file_size: 文件大小（字节）
            
        Returns:
            tuple[bool, Optional[str]]: (是否允许转发, 限制信息)
        """
        if file_size < 0:
            return False, "文件大小无效"
            
        limits = await self.get_traffic_limits()
        
        if not limits or limits.get('enabled') == 0:
            return True, None
        
        if file_size > limits.get('per_file_limit', 0):
            return False, f"文件大小超过限制 ({self.format_bytes(limits['per_file_limit'])})"
        
        traffic = await self.get_user_traffic(user_id)
        if not traffic:
            return True, None
        
        daily_limit = limits.get('daily_limit', 0)
        monthly_limit = limits.get('monthly_limit', 0)
        
        if traffic.get('daily_download', 0) + file_size > daily_limit:
            remaining = max(0, daily_limit - traffic.get('daily_download', 0))
            return False, f"今日流量不足，剩余 {self.format_bytes(remaining)}"
        
        if traffic.get('monthly_download', 0) + file_size > monthly_limit:
            remaining = max(0, monthly_limit - traffic.get('monthly_download', 0))
            return False, f"本月流量不足，剩余 {self.format_bytes(remaining)}"
        
        return True, None
    
    @staticmethod
    def format_bytes(bytes_num: int) -> str:
        """格式化字节数
        
        Args:
            bytes_num: 字节数
            
        Returns:
            str: 格式化后的字符串
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_num < 1024.0:
                return f"{bytes_num:.2f} {unit}"
            bytes_num /= 1024.0
        return f"{bytes_num:.2f} PB"
    
    # ==================== SESSION管理 ====================
    
    async def save_session(self, user_id: int, session_string: str) -> bool:
        """保存SESSION字符串
        
        Args:
            user_id: 用户ID
            session_string: SESSION字符串
            
        Returns:
            bool: 操作是否成功
        """
        async with self._lock:
            if self.db is None:
                return False
            
            try:
                self._ensure_connection()
                result = self.db.users.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {
                            "session_string": session_string,
                            "session_updated": datetime.now()
                        }
                    },
                    upsert=True
                )
                return True
            except Exception as e:
                logger.error(f"保存会话失败: {e}")
                return False
    
    async def get_session(self, user_id: int) -> Optional[str]:
        """获取SESSION字符串
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[str]: SESSION字符串，如果不存在则返回None
        """
        async with self._lock:
            if self.db is None:
                return None
            
            try:
                self._ensure_connection()
                user = self.db.users.find_one({"user_id": user_id})
                return user.get("session_string") if user else None
            except Exception as e:
                logger.error(f"获取会话失败: {e}")
                return None
    
    async def delete_session(self, user_id: int) -> bool:
        """删除SESSION字符串
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 操作是否成功
        """
        async with self._lock:
            if self.db is None:
                return False
            
            try:
                self._ensure_connection()
                # 先检查用户是否存在且有session
                user = self.db.users.find_one({"user_id": user_id})
                if not user or not user.get("session_string"):
                    # 用户不存在或没有session，认为删除成功
                    return True
                
                result = self.db.users.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {"session_string": None},
                        "$unset": {"session_updated": ""}
                    }
                )
                return True
            except Exception as e:
                logger.error(f"删除会话失败: {e}")
                return False
    
    async def get_all_sessions(self) -> List[Dict[str, Any]]:
        """获取所有SESSION
        
        Returns:
            List[Dict[str, Any]]: SESSION列表
        """
        async with self._lock:
            if self.db is None:
                return []
            
            try:
                self._ensure_connection()
                users = list(
                    self.db.users.find(
                        {"session_string": {"$ne": None}},
                        {"user_id": 1, "session_string": 1, "username": 1}
                    )
                )
                return users
            except Exception as e:
                logger.error(f"获取所有会话失败: {e}")
                return []

    async def reset_daily_traffic(self) -> bool:
        """重置所有用户的每日流量统计
        
        Returns:
            bool: 操作是否成功
        """
        async with self._lock:
            if self.db is None:
                return False
            
            try:
                self._ensure_connection()
                # 重置所有用户的每日流量统计
                result = self.db.users.update_many(
                    {},  # 匹配所有用户
                    {
                        "$set": {
                            "daily_upload": 0,
                            "daily_download": 0
                        }
                    }
                )
                logger.info(f"重置了 {result.modified_count} 个用户的每日流量统计")
                return True
            except Exception as e:
                logger.error(f"重置每日流量统计失败: {e}")
                return False

    async def reset_monthly_traffic(self) -> bool:
        """重置所有用户的每月流量统计
        
        Returns:
            bool: 操作是否成功
        """
        async with self._lock:
            if self.db is None:
                return False
            
            try:
                self._ensure_connection()
                # 重置所有用户的每月流量统计
                result = self.db.users.update_many(
                    {},  # 匹配所有用户
                    {
                        "$set": {
                            "monthly_upload": 0,
                            "monthly_download": 0
                        }
                    }
                )
                logger.info(f"重置了 {result.modified_count} 个用户的每月流量统计")
                return True
            except Exception as e:
                logger.error(f"重置每月流量统计失败: {e}")
                return False

    async def reset_all_traffic(self) -> bool:
        """重置所有流量统计（包括历史累计）
        
        Returns:
            bool: 操作是否成功
        """
        async with self._lock:
            if self.db is None:
                return False
            
            try:
                self._ensure_connection()
                # 重置所有流量统计（包括历史累计）
                result = self.db.users.update_many(
                    {},  # 匹配所有用户
                    {
                        "$set": {
                            "daily_upload": 0,
                            "daily_download": 0,
                            "monthly_upload": 0,
                            "monthly_download": 0,
                            "total_upload": 0,
                            "total_download": 0
                        }
                    }
                )
                logger.info(f"重置了 {result.modified_count} 个用户的所有流量统计")
                return True
            except Exception as e:
                logger.error(f"重置所有流量统计失败: {e}")
                return False

    async def clear_forward_history(self) -> bool:
        """清除所有转发历史记录
        
        Returns:
            bool: 操作是否成功
        """
        async with self._lock:
            if self.db is None:
                return False
            
            try:
                self._ensure_connection()
                # 删除所有转发历史记录
                result = self.db.message_history.delete_many({})
                logger.info(f"清除了 {result.deleted_count} 条转发历史记录")
                return True
            except Exception as e:
                logger.error(f"清除转发历史记录失败: {e}")
                return False


# 全局数据库管理器实例
db_manager = DatabaseManager()


# 添加额外的数据库方法
async def reset_daily_traffic() -> bool:
    """重置所有用户的每日流量统计
    
    Returns:
        bool: 操作是否成功
    """
    return await db_manager.reset_daily_traffic()


async def reset_monthly_traffic() -> bool:
    """重置所有用户的每月流量统计
    
    Returns:
        bool: 操作是否成功
    """
    return await db_manager.reset_monthly_traffic()


async def reset_all_traffic() -> bool:
    """重置所有流量统计（包括历史累计）
    
    Returns:
        bool: 操作是否成功
    """
    return await db_manager.reset_all_traffic()


async def clear_forward_history() -> bool:
    """清除所有转发历史记录
    
    Returns:
        bool: 操作是否成功
    """
    return await db_manager.clear_forward_history()