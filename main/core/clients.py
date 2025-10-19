"""Telegram客户端管理模块"""
import logging
import os
from typing import Optional, Dict, Any
from pyrogram import Client
from telethon.sessions import StringSession
from telethon.sync import TelegramClient

from ..config import settings
from ..services.session_service import session_service
from ..utils.security import security_manager

logger = logging.getLogger(__name__)


class ClientManager:
    """Telegram客户端管理器"""
    
    def __init__(self):
        self.bot: Optional[TelegramClient] = None
        self.userbot: Optional[Client] = None
        self.pyrogram_bot: Optional[Client] = None
        self.session_svc = session_service
        # 延迟获取代理配置，直到需要时
        self._proxy_config = None
        
    @property
    def proxy_config(self) -> Optional[Dict[str, Any]]:
        """动态获取代理配置"""
        if self._proxy_config is None:
            self._proxy_config = self._get_proxy_config()
        return self._proxy_config
        
    def _get_proxy_config(self) -> Optional[Dict[str, Any]]:
        """获取代理配置"""
        # 检查环境变量中的代理配置
        proxy_scheme = os.getenv('TELEGRAM_PROXY_SCHEME')
        proxy_host = os.getenv('TELEGRAM_PROXY_HOST')
        proxy_port = os.getenv('TELEGRAM_PROXY_PORT')
        
        if proxy_scheme and proxy_host and proxy_port:
            try:
                proxy_port = int(proxy_port)
                logger.info(f"检测到代理配置: {proxy_scheme}://{proxy_host}:{proxy_port}")
                
                # 返回代理配置字典
                return {
                    'scheme': proxy_scheme,
                    'hostname': proxy_host,
                    'port': proxy_port
                }
            except ValueError:
                logger.warning("代理端口格式无效")
                return None
        else:
            # 检查是否配置了使用其他代理
            other_proxy_url = os.getenv('OTHER_PROXY_URL')
            if other_proxy_url:
                logger.info(f"使用其他代理: {other_proxy_url}")
                return {
                    'scheme': 'http',
                    'hostname': other_proxy_url,
                    'port': 8080
                }
        
        return None
    
    def _get_telethon_proxy(self) -> Optional[tuple]:
        """获取Telethon代理配置"""
        if self.proxy_config:
            scheme = self.proxy_config['scheme']
            # 支持SOCKS5代理
            if scheme in ['socks5', 'socks4']:
                return (
                    scheme,
                    self.proxy_config['hostname'],
                    self.proxy_config['port']
                )
            # Telethon只支持http代理，不支持https
            elif scheme == 'https':
                scheme = 'http'  # Telethon不支持https代理
            return (
                scheme,
                self.proxy_config['hostname'],
                self.proxy_config['port']
            )
        return None
    
    def _get_pyrogram_proxy(self) -> Optional[Dict[str, Any]]:
        """获取Pyrogram代理配置"""
        return self.proxy_config
    
    async def initialize_clients(self):
        """初始化所有Telegram客户端"""
        try:
            # 初始化Telethon bot客户端
            self._init_telethon_bot()
            
            # 初始化Pyrogram bot客户端
            self._init_pyrogram_bot()
            
            # 初始化userbot客户端
            await self._init_userbot()
            
            # 启动Telethon bot客户端
            if self.bot:
                await self.bot.start(bot_token=settings.BOT_TOKEN)
                logger.info("Telethon bot客户端启动成功")
            
            # 启动Pyrogram bot客户端
            if self.pyrogram_bot:
                await self.pyrogram_bot.start()
                logger.info("Pyrogram bot客户端启动成功")
            
            logger.info("所有Telegram客户端初始化完成")
        except Exception as e:
            logger.error(f"初始化客户端失败: {e}")
            raise
    
    def _init_telethon_bot(self):
        """初始化Telethon bot客户端"""
        try:
            # 掩码敏感信息用于日志
            masked_token = security_manager.mask_sensitive_data(settings.BOT_TOKEN, 10)
            logger.info(f"正在启动Telethon bot客户端 (Token: {masked_token})")
            
            # 获取代理配置
            telethon_proxy = self._get_telethon_proxy()
            
            # 创建Telethon客户端
            if telethon_proxy:
                logger.info(f"使用代理: {telethon_proxy[0]}://{telethon_proxy[1]}:{telethon_proxy[2]}")
                self.bot = TelegramClient(
                    'bot', 
                    settings.API_ID, 
                    settings.API_HASH,
                    proxy=telethon_proxy
                )
            else:
                self.bot = TelegramClient('bot', settings.API_ID, settings.API_HASH)
            
            logger.info("Telethon bot客户端初始化完成")
        except Exception as e:
            logger.error(f"Telethon bot初始化失败: {e}")
            raise
    
    def _init_pyrogram_bot(self):
        """初始化Pyrogram bot客户端"""
        try:
            # 掩码敏感信息用于日志
            masked_token = security_manager.mask_sensitive_data(settings.BOT_TOKEN, 10)
            logger.info(f"正在启动Pyrogram bot客户端 (Token: {masked_token})")
            
            # 获取代理配置
            pyrogram_proxy = self._get_pyrogram_proxy()
            
            # 创建Pyrogram客户端
            if pyrogram_proxy:
                logger.info(f"使用代理: {pyrogram_proxy['scheme']}://{pyrogram_proxy['hostname']}:{pyrogram_proxy['port']}")
                self.pyrogram_bot = Client(
                    "SaveRestricted",
                    bot_token=settings.BOT_TOKEN,
                    api_id=settings.API_ID,
                    api_hash=settings.API_HASH,
                    proxy=pyrogram_proxy
                )
            else:
                self.pyrogram_bot = Client(
                    "SaveRestricted",
                    bot_token=settings.BOT_TOKEN,
                    api_id=settings.API_ID,
                    api_hash=settings.API_HASH
                )
            
            logger.info("Pyrogram bot客户端初始化完成")
        except Exception as e:
            logger.error(f"Pyrogram bot初始化失败: {e}")
            raise
    
    async def _init_userbot(self):
        """初始化userbot客户端"""
        try:
            # 如果没有设置SESSION，尝试从会话服务获取SESSION
            if not settings.SESSION:
                user_session = await self.session_svc.get_session(settings.AUTH)
                if user_session:
                    settings.SESSION = user_session
                    logger.info("从会话服务加载SESSION成功")
            
            if settings.SESSION:
                # 验证SESSION格式
                if not self._validate_session(settings.SESSION):
                    logger.warning("SESSION格式无效，Userbot将以有限功能运行")
                    self.userbot = None
                    return
                
                # 掩码敏感信息用于日志
                masked_session = security_manager.mask_sensitive_data(settings.SESSION, 15)
                logger.info(f"正在启动Userbot客户端 (Session: {masked_session})")
                
                # 获取代理配置
                pyrogram_proxy = self._get_pyrogram_proxy()
                
                # 创建Pyrogram客户端（Userbot）
                if pyrogram_proxy:
                    logger.info(f"Userbot使用代理: {pyrogram_proxy['scheme']}://{pyrogram_proxy['hostname']}:{pyrogram_proxy['port']}")
                    self.userbot = Client(
                        "saverestricted", 
                        session_string=settings.SESSION, 
                        api_hash=settings.API_HASH, 
                        api_id=settings.API_ID,
                        proxy=pyrogram_proxy
                    )
                else:
                    self.userbot = Client(
                        "saverestricted", 
                        session_string=settings.SESSION, 
                        api_hash=settings.API_HASH, 
                        api_id=settings.API_ID
                    )
                
                await self.userbot.start()
                logger.info("Userbot客户端启动成功")
            else:
                logger.warning("未配置SESSION，Userbot将以有限功能运行")
                self.userbot = None
        except Exception as e:
            logger.error(f"Userbot启动失败: {e}")
            self.userbot = None
    
    def _validate_session(self, session_string: str) -> bool:
        """验证SESSION格式"""
        if not session_string or len(session_string) < 10:
            return False
        
        # 清理字符串，移除所有非base64字符
        import re
        cleaned_session = re.sub(r'[^A-Za-z0-9+/=]', '', session_string)
        
        # 检查是否符合基本的Base64模式
        if not re.match(r'^[A-Za-z0-9+/]*={0,2}$', cleaned_session):
            self.logger.warning(f"SESSION不符合Base64模式: {cleaned_session[:50]}...")
            return False
        
        # 检查长度是否符合Base64要求（4的倍数）
        if len(cleaned_session) % 4 != 0:
            self.logger.warning(f"SESSION长度不是4的倍数: {len(cleaned_session)}")
            return False
        
        # 尝试解码以验证格式
        try:
            import base64
            base64.b64decode(cleaned_session)
            return True
        except Exception as e:
            self.logger.warning(f"SESSION解码失败: {e}")
            return False
    
    async def stop_clients(self):
        """停止所有客户端"""
        try:
            logger.info("正在停止所有客户端...")
            
            if self.bot:
                await self.bot.disconnect()
                logger.info("Telethon bot客户端已停止")
                
            if self.pyrogram_bot:
                await self.pyrogram_bot.stop()
                logger.info("Pyrogram bot客户端已停止")
                
            if self.userbot:
                await self.userbot.stop()
                logger.info("Userbot客户端已停止")
                
            logger.info("所有客户端已停止")
        except Exception as e:
            logger.error(f"停止客户端时出错: {e}")
    
    async def refresh_userbot_session(self, new_session: str) -> bool:
        """刷新Userbot SESSION"""
        try:
            if not self._validate_session(new_session):
                logger.error("新SESSION格式无效")
                return False
            
            # 停止当前userbot
            if self.userbot:
                await self.userbot.stop()
            
            # 更新配置
            settings.SESSION = new_session
            
            # 重新初始化userbot
            await self._init_userbot()
            
            logger.info("Userbot SESSION刷新成功")
            return True
        except Exception as e:
            logger.error(f"刷新Userbot SESSION时出错: {e}")
            return False
    
    def get_client_status(self) -> dict:
        """获取客户端状态"""
        return {
            "telethon_bot": self.bot is not None,
            "pyrogram_bot": self.pyrogram_bot is not None and self.pyrogram_bot.is_connected,
            "userbot": self.userbot is not None and self.userbot.is_connected,
            "session_configured": settings.SESSION is not None,
            "proxy_enabled": self.proxy_config is not None
        }


# 全局客户端管理器实例
client_manager = ClientManager()