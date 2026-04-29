"""数据库管理模块

该模块提供MongoDB数据库的连接管理和数据操作功能，
包括用户管理、消息记录、流量统计等核心数据的存储和查询。
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, date

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError, ServerSelectionTimeoutError
from bson.objectid import ObjectId

from ..config import settings
from ..exceptions.base import BaseBotException

logger = logging.getLogger(__name__)


class DatabaseConnectionError(BaseBotException):
    def __init__(self, message: str) -> None:
        super().__init__(message, "DATABASE_CONNECTION_ERROR")


class DatabaseOperationError(BaseBotException):
    def __init__(self, message: str) -> None:
        super().__init__(message, "DATABASE_OPERATION_ERROR")


class DatabaseManager:
    def __init__(self) -> None:
        self.client: Optional[MongoClient] = None
        self.db = None
        self._last_health_check = None
        self._connection_errors = 0
        self._max_connection_errors = 3
        self._connecting = False

    def _connect(self) -> None:
        if not settings.MONGO_DB:
            logger.warning("未配置MongoDB连接字符串")
            return

        try:
            logger.info("正在连接MongoDB...")
            pool_config = {
                'serverSelectionTimeoutMS': 10000,
                'connectTimeoutMS': 10000,
                'socketTimeoutMS': 30000,
                'maxPoolSize': 20,
                'minPoolSize': 5,
                'maxIdleTimeMS': 60000,
                'waitQueueTimeoutMS': 10000,
                'retryWrites': True,
                'retryReads': True,
                'connect': False
            }

            self.client = MongoClient(settings.MONGO_DB, **pool_config)
            self.client.admin.command('ping')
            self.db = self.client['tg_content_bot']
            logger.info("MongoDB数据库连接成功")

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
        try:
            if self.db is None:
                return

            self.db.users.create_index("user_id", unique=True)
            self.db.users.create_index("is_premium")
            self.db.message_history.create_index([("user_id", 1), ("forward_date", -1)])
            self.db.batch_tasks.create_index([("user_id", 1), ("start_time", -1)])
            self.db.users.create_index("last_reset_daily")
            self.db.users.create_index("last_reset_monthly")

            logger.info("数据库索引创建完成")
        except Exception as e:
            logger.warning(f"创建索引失败: {e}")

    def _ensure_connection(self) -> None:
        if self._connecting:
            return
        logger.info(f"检查数据库连接: client={self.client is not None}, db={self.db is not None}")
        if not self.client:
            if not settings.MONGO_DB:
                logger.debug("未配置MongoDB连接字符串，跳过连接检查")
                return
            self._connecting = True
            try:
                self._connect()
            finally:
                self._connecting = False
            return

        try:
            self.client.admin.command('ping')
            self._connection_errors = 0
            self._last_health_check = datetime.now()
        except Exception as e:
            self._connection_errors += 1
            logger.warning(f"数据库连接失效 ({self._connection_errors}/{self._max_connection_errors}): {e}")

            if self._connection_errors >= self._max_connection_errors:
                logger.error("数据库连接错误次数过多，尝试重新连接")
                self._connecting = True
                try:
                    self._connect()
                finally:
                    self._connecting = False
            else:
                logger.warning("数据库连接暂时性错误，继续使用现有连接")

    def get_connection_stats(self) -> Dict[str, Any]:
        if not self.client:
            return {"status": "disconnected", "pool_size": 0, "connection_errors": self._connection_errors}

        try:
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
        if not settings.MONGO_DB:
            return False
        if not self.client or self.db is None:
            return False

        try:
            self.client.admin.command('ping')
            return True
        except Exception:
            return False

    async def add_user(self, user_id: int, username: Optional[str] = None,
                      first_name: Optional[str] = None, last_name: Optional[str] = None,
                      is_authorized: bool = False) -> bool:
        if self.db is None:
            return False

        try:
            self._ensure_connection()
            now = datetime.now()
            self.db.users.update_one(
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
                        "is_authorized": is_authorized,
                        "is_premium": False,
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
        if self.db is None:
            return None

        try:
            self._ensure_connection()
            return self.db.users.find_one({"user_id": user_id})
        except Exception as e:
            logger.error(f"获取用户失败: {e}")
            return None

    async def is_user_banned(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        return user and user.get('is_banned', False)

    async def is_user_premium(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        return user and user.get('is_premium', False)

    async def set_user_premium(self, user_id: int, is_premium: bool) -> bool:
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
        if self.db is None:
            return 0

        try:
            self._ensure_connection()
            return self.db.users.count_documents({})
        except Exception as e:
            logger.error(f"获取用户数失败: {e}")
            return 0

    async def add_forward(self, user_id: int, message_link: str, message_id: int,
                         chat_id: str, media_type: str, file_size: int = 0, status: str = "success") -> bool:
        if self.db is None:
            return False

        try:
            self._ensure_connection()
            now = datetime.now()

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

    async def unauthorized_user(self, user_id: int) -> bool:
        if self.db is None:
            return False

        try:
            self._ensure_connection()
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
        from ..config import settings
        if user_id in settings.get_auth_users():
            return True

        user = await self.get_user(user_id)
        return user and user.get('is_authorized', False)

    async def get_forward_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
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
        if self.db is None:
            return []

        try:
            self._ensure_connection()
            cursor = self.db.message_history.find({}).sort("forward_date", -1).skip(offset).limit(limit)
            history = list(cursor)

            result = []
            for h in history:
                record = {}
                for key, value in h.items():
                    try:
                        if hasattr(value, '__class__') and 'bson.objectid.ObjectId' in str(type(value)):
                            record[key] = str(value)
                        elif hasattr(value, 'isoformat') and callable(getattr(value, 'isoformat', None)):
                            record[key] = value.isoformat()
                        else:
                            record[key] = value
                    except Exception as e:
                        logger.error(f"处理字段 {key} 时出错: {e}")
                        record[key] = value

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
            return []

    async def get_total_forwards(self) -> int:
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

    async def create_batch_task(self, user_id: int, start_link: str, message_count: int) -> Optional[str]:
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
        if not self.db or not task_id:
            return False

        try:
            obj_id = ObjectId(task_id)
        except Exception:
            logger.error(f"无效的task_id格式: {task_id}")
            return False

        try:
            self._ensure_connection()
            result = self.db.batch_tasks.update_one(
                {"_id": obj_id},
                {"$set": {"completed_count": completed_count}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"更新批量任务进度失败: {e}")
            return False

    async def complete_batch_task(self, task_id: str) -> bool:
        if not self.db or not task_id:
            return False

        try:
            obj_id = ObjectId(task_id)
        except Exception:
            logger.error(f"无效的task_id格式: {task_id}")
            return False

        try:
            self._ensure_connection()
            result = self.db.batch_tasks.update_one(
                {"_id": obj_id},
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

    async def add_traffic(self, user_id: int, upload_bytes: int = 0, download_bytes: int = 0) -> bool:
        if not self.db or upload_bytes < 0 or download_bytes < 0:
            return False

        try:
            self._ensure_connection()
            now = datetime.now()
            today = now.date().isoformat()
            month = now.strftime("%Y-%m")

            self.db.users.update_one(
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

            return True
        except Exception as e:
            logger.error(f"添加流量统计失败: {e}")
            return False

    async def get_user_traffic(self, user_id: int) -> Optional[Dict[str, int]]:
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
        if self.db is None:
            return None

        try:
            self._ensure_connection()
            today = date.today().isoformat()
            today_result = self.db.users.aggregate([
                {"$match": {"last_reset_daily": today}},
                {"$group": {"_id": None, "download": {"$sum": "$daily_download"}}}
            ])
            today_data = list(today_result)

            month = datetime.now().strftime("%Y-%m")
            month_result = self.db.users.aggregate([
                {"$match": {"last_reset_monthly": month}},
                {"$group": {"_id": None, "download": {"$sum": "$monthly_download"}}}
            ])
            month_data = list(month_result)

            total_result = self.db.users.aggregate([
                {"$group": {"_id": None, "upload": {"$sum": "$total_upload"}, "download": {"$sum": "$total_download"}}}
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
        if self.db is None:
            return None

        try:
            self._ensure_connection()
            limits = self.db.settings.find_one({"type": "traffic_limits"})
            if not limits:
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
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_num < 1024.0:
                return f"{bytes_num:.2f} {unit}"
            bytes_num /= 1024.0
        return f"{bytes_num:.2f} PB"

    async def save_session(self, user_id: int, session_string: str) -> bool:
        try:
            self._ensure_connection()
            if self.db is None:
                logger.error("数据库连接失败，无法保存SESSION")
                return False

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
            logger.info(f"SESSION保存结果: user_id={user_id}, modified={result.modified_count}, upserted={result.upserted_id}")
            return True
        except Exception as e:
            logger.error(f"保存会话失败: {e}")
            return False

    async def get_session(self, user_id: int) -> Optional[str]:
        if self.db is None:
            self._ensure_connection()

        if self.db is None:
            logger.error("get_session: 无法连接数据库")
            return None

        try:
            user = self.db.users.find_one({"user_id": user_id})
            if not user:
                logger.warning(f"get_session: user {user_id} not found")
                return None

            session = user.get("session_string")
            logger.info(f"get_session: found session, length: {len(session) if session else 0}")
            return session
        except Exception as e:
            logger.error(f"获取会话失败: {e}")
            return None

    async def delete_session(self, user_id: int) -> bool:
        if self.db is None:
            return False

        try:
            self._ensure_connection()
            user = self.db.users.find_one({"user_id": user_id})
            if not user or not user.get("session_string"):
                return True

            self.db.users.update_one(
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
        if self.db is None:
            return False

        try:
            self._ensure_connection()
            result = self.db.users.update_many(
                {},
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
        if self.db is None:
            return False

        try:
            self._ensure_connection()
            result = self.db.users.update_many(
                {},
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
        if self.db is None:
            return False

        try:
            self._ensure_connection()
            result = self.db.users.update_many(
                {},
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
        if self.db is None:
            return False

        try:
            self._ensure_connection()
            result = self.db.message_history.delete_many({})
            logger.info(f"清除了 {result.deleted_count} 条转发历史记录")
            return True
        except Exception as e:
            logger.error(f"清除转发历史记录失败: {e}")
            return False

    async def get_bot_session(self, api_id: int) -> Optional[bytes]:
        """从数据库获取 BotClient.session"""
        if self.db is None:
            return None

        try:
            self._ensure_connection()
            result = self.db.bot_sessions.find_one({"api_id": api_id})
            if result and "session_data" in result:
                return result["session_data"]
            return None
        except Exception as e:
            logger.error(f"获取 BotClient.session 失败: {e}")
            return None

    async def save_bot_session(self, api_id: int, session_data: bytes) -> bool:
        """保存 BotClient.session 到数据库"""
        if self.db is None:
            return False

        try:
            self._ensure_connection()
            self.db.bot_sessions.update_one(
                {"api_id": api_id},
                {"$set": {
                    "session_data": session_data,
                    "updated_at": datetime.now()
                }},
                upsert=True
            )
            logger.info(f"BotClient.session 已保存到数据库")
            return True
        except Exception as e:
            logger.error(f"保存 BotClient.session 失败: {e}")
            return False


db_manager = DatabaseManager()
