"""Telegram客户端管理模块"""
import logging
import os
import sqlite3
from typing import Dict, Any, Optional

from pyrogram import Client as PyrogramClient
from ..config import settings
from ..services.session_service import session_service
from ..utils.security import security_manager
from ..utils.session_utils import sanitize_pyrogram_session, validate_pyrogram_session

logger = logging.getLogger(__name__)


class ClientManager:
    """Telegram客户端管理器"""
    
    def __init__(self):
        self.bot: Optional[PyrogramClient] = None
        self.userbot: Optional[PyrogramClient] = None
        self.session_svc = session_service
        self.logger = logging.getLogger(__name__)
    
    async def initialize_clients(self):
        """初始化所有Telegram客户端"""
        try:
            logger.info("开始初始化Telegram客户端...")
            await self._initialize_all_clients()
            logger.info("所有Telegram客户端初始化完成")
        except Exception as e:
            logger.error(f"初始化客户端失败: {e}")
            raise
    
    async def _initialize_all_clients(self):
        """初始化并启动所有客户端"""
        await self._load_bot_session_from_db()
        self._create_pyrogram_bot()
        await self._start_pyrogram_bot()
        await self._save_bot_session_to_db()
        await self._initialize_userbot()
    
    async def _load_bot_session_from_db(self):
        """从数据库加载 BotClient.session"""
        try:
            from ..core.database import db_manager
            
            # 确保数据库已连接
            db_manager._ensure_connection()
            if db_manager.db is None:
                logger.info("数据库未连接，跳过加载 BotClient.session")
                return
            
            logger.info(f"尝试从数据库加载 BotClient.session，API_ID={settings.API_ID}")
            bot_session = await db_manager.get_bot_session(settings.API_ID)
            if bot_session:
                session_dir = os.environ.get("SESSION_DIR", "/app/sessions")
                os.makedirs(session_dir, exist_ok=True)
                session_path = os.path.join(session_dir, "BotClient.session")
                
                with open(session_path, 'wb') as f:
                    f.write(bot_session)
                logger.info(f"从数据库加载 BotClient.session 成功，大小: {len(bot_session)} 字节")
            else:
                logger.info("数据库中无 BotClient.session")
        except Exception as e:
            logger.warning(f"从数据库加载 BotClient.session 失败: {e}")
    
    async def _save_bot_session_to_db(self):
        """保存 BotClient.session 到数据库"""
        try:
            if not self.bot or not self.bot.is_connected:
                return
            
            session_dir = os.environ.get("SESSION_DIR", "/app/sessions")
            session_path = os.path.join(session_dir, "BotClient.session")
            
            if os.path.exists(session_path):
                with open(session_path, 'rb') as f:
                    session_data = f.read()
                
                from ..core.database import db_manager
                await db_manager.save_bot_session(settings.API_ID, session_data)
                logger.info(f"BotClient.session 已保存到数据库，大小: {len(session_data)} 字节")
        except Exception as e:
            logger.warning(f"保存 BotClient.session 到数据库失败: {e}")
    
    def _create_pyrogram_bot(self):
        """创建Pyrogram bot客户端实例"""
        try:
            masked_token = security_manager.mask_sensitive_data(settings.BOT_TOKEN, 10)
            logger.info(f"正在创建Pyrogram bot客户端 (Token: {masked_token})")
            
            # 使用持久化的session文件路径
            session_dir = os.environ.get("SESSION_DIR", "/app/sessions")
            os.makedirs(session_dir, exist_ok=True)
            session_path = os.path.join(session_dir, "BotClient")
            logger.info(f"Session文件路径: {session_path}.session")
            
            self.bot = PyrogramClient(
                session_path,
                bot_token=settings.BOT_TOKEN,
                api_id=settings.API_ID,
                api_hash=settings.API_HASH,
                app_version="10.2.0",
                device_model="iPhone 15 Pro Max",
                system_version="iOS 17.5",
                lang_code="en",
                sleep_threshold=60
            )
            
            logger.info("Pyrogram bot客户端实例创建完成")
        except Exception as e:
            logger.error(f"创建Pyrogram bot客户端失败: {e}")
            raise
    
    async def _start_pyrogram_bot(self):
        """启动Pyrogram bot客户端"""
        if self.bot:
            try:
                await self.bot.start()
                logger.info("Pyrogram bot客户端启动成功")
            except Exception as e:
                logger.error(f"Pyrogram bot启动失败: {e}")
                self.bot = None
    
    async def _initialize_userbot(self):
        """初始化Userbot客户端"""
        try:
            if not settings.SESSION:
                await self._load_session_from_service()
            
            if settings.SESSION:
                await self._create_and_start_userbot()
            else:
                logger.warning("未配置SESSION，Userbot将无法运行")
        except Exception as e:
            logger.error(f"初始化Userbot失败: {e}")
            self.userbot = None
    
    async def _load_session_from_service(self):
        """从会话服务加载SESSION"""
        auth_users = settings.get_auth_users()
        if auth_users:
            for user_id in auth_users:
                session_data = await self.session_svc.get_session(user_id)
                if session_data:
                    settings.SESSION = session_data
                    logger.info(f"从数据库加载用户 {user_id} 的SESSION成功")
                    return
        logger.warning("未找到授权用户的SESSION")
    
    async def _create_and_start_userbot(self):
        """创建并启动Userbot客户端"""
        session_string = settings.SESSION
        corrected_session = self._sanitize_session_string(session_string)
        
        masked_session = security_manager.mask_sensitive_data(corrected_session, 15)
        logger.info(f"正在启动Userbot客户端 (Session: {masked_session})")
        
        # 使用内存session（不持久化）
        userbot = PyrogramClient(
            "Userbot",
            session_string=corrected_session,
            api_hash=settings.API_HASH,
            api_id=settings.API_ID,
            app_version="Pyrogram 2.0.106",
            device_model="Session Generator",
            system_version="Linux 5.4",
            lang_code="en",
            sleep_threshold=60,
            in_memory=True
        )
        
        try:
            await userbot.start()
            logger.info("Userbot客户端启动成功")
            
            if userbot.is_connected:
                self.userbot = userbot
            else:
                logger.warning("Userbot客户端已启动但未连接")
                await userbot.stop()
        except Exception as e:
            await self._handle_userbot_start_error(e, corrected_session)
    
    def _sanitize_session_string(self, session_string: str) -> str:
        """清理和验证SESSION字符串"""
        if not session_string:
            logger.warning("SESSION字符串为空")
            return session_string
        
        cleaned = sanitize_pyrogram_session(session_string)
        
        if validate_pyrogram_session(cleaned):
            logger.info(f"SESSION验证通过，长度: {len(cleaned)}")
        else:
            logger.warning(f"SESSION验证失败，长度: {len(cleaned)}")
        
        return cleaned
    
    async def _handle_userbot_start_error(self, error: Exception, session_string: str):
        """处理Userbot启动错误"""
        error_msg = str(error).lower()
        logger.error(f"Userbot启动失败: {error}")
        
        session_error_keywords = [
            "invalid session", 
            "session expired", 
            "session revoked", 
            "auth key not found",
            "406 update_app_to_login",
            "unpack requires a buffer"
        ]
        
        if any(keyword in error_msg for keyword in session_error_keywords):
            logger.warning("检测到无效SESSION，正在清理...")
            try:
                auth_users = settings.get_auth_users()
                if auth_users:
                    user_id = auth_users[0]
                    await self.session_svc.delete_session(user_id)
                    logger.info(f"已清理用户 {user_id} 的无效SESSION")
                settings.SESSION = None
            except Exception as e:
                logger.error(f"清理SESSION时出错: {e}")
        
        self.userbot = None
        logger.info("Userbot启动失败，但机器人将继续运行")
    
    async def stop_clients(self):
        """停止所有客户端"""
        try:
            logger.info("正在停止所有客户端...")
            
            if self.bot:
                await self.bot.stop()
                logger.info("Pyrogram bot客户端已停止")
                self.bot = None
            
            if self.userbot:
                await self.userbot.stop()
                logger.info("Userbot客户端已停止")
                self.userbot = None
            
            logger.info("所有客户端已停止")
        except Exception as e:
            logger.error(f"停止客户端时出错: {e}")
    
    async def refresh_userbot_session(self, new_session: str) -> bool:
        """刷新Userbot SESSION"""
        try:
            if self.userbot:
                await self.userbot.stop()
                self.userbot = None
            
            settings.SESSION = new_session
            await self._initialize_userbot()
            
            success = self.userbot is not None and self.userbot.is_connected
            if success:
                logger.info("Userbot SESSION刷新成功")
            else:
                logger.warning("Userbot SESSION刷新完成，但客户端未连接")
            
            return success
        except Exception as e:
            logger.error(f"刷新Userbot SESSION时出错: {e}")
            return False
    
    def get_client_status(self) -> Dict[str, Any]:
        """获取客户端状态"""
        return {
            "pyrogram_bot": self.bot is not None and self.bot.is_connected,
            "userbot": self.userbot is not None and self.userbot.is_connected,
            "session_configured": settings.SESSION is not None
        }


# 全局客户端管理器实例
client_manager = ClientManager()