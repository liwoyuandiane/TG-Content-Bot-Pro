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
        self.logger = logging.getLogger(__name__)
        
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
        
        # 检查代理认证信息
        proxy_username = settings.TELEGRAM_PROXY_USERNAME
        proxy_password = settings.TELEGRAM_PROXY_PASSWORD
        
        if proxy_scheme and proxy_host and proxy_port:
            try:
                proxy_port = int(proxy_port)
                logger.info(f"检测到代理配置: {proxy_scheme}://{proxy_host}:{proxy_port}")
                
                # 返回代理配置字典
                proxy_config = {
                    'scheme': proxy_scheme,
                    'hostname': proxy_host,
                    'port': proxy_port
                }
                
                # 如果提供了认证信息，添加到配置中
                if proxy_username and proxy_password:
                    proxy_config['username'] = proxy_username
                    proxy_config['password'] = proxy_password
                    logger.info("代理认证信息已配置")
                
                return proxy_config
            except ValueError:
                logger.warning("代理端口格式无效")
                return None
        else:
            # 检查是否配置了使用其他代理
            other_proxy_url = os.getenv('OTHER_PROXY_URL')
            if other_proxy_url:
                logger.info(f"使用其他代理: {other_proxy_url}")
                proxy_config = {
                    'scheme': 'http',
                    'hostname': other_proxy_url,
                    'port': 8080
                }
                
                # 如果提供了认证信息，添加到配置中
                if proxy_username and proxy_password:
                    proxy_config['username'] = proxy_username
                    proxy_config['password'] = proxy_password
                    logger.info("代理认证信息已配置")
                
                return proxy_config
        
        return None
    
    def _create_pyrogram_proxy_config(self, proxy_config: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """创建Pyrogram代理配置"""
        if not proxy_config:
            return None
            
        # 为Pyrogram创建代理配置（处理认证）
        pyrogram_proxy_config = {
            'scheme': proxy_config['scheme'],
            'hostname': proxy_config['hostname'],
            'port': proxy_config['port']
        }
        
        # 如果有认证信息，添加到配置中
        if 'username' in proxy_config and 'password' in proxy_config:
            pyrogram_proxy_config['username'] = proxy_config['username']
            pyrogram_proxy_config['password'] = proxy_config['password']
        
        return pyrogram_proxy_config
    
    def _get_telethon_proxy(self) -> Optional[tuple]:
        """获取Telethon代理配置"""
        if self.proxy_config:
            scheme = self.proxy_config['scheme']
            hostname = self.proxy_config['hostname']
            port = self.proxy_config['port']
            
            # 支持SOCKS5代理
            if scheme in ['socks5', 'socks4']:
                # 如果有认证信息，包含在代理配置中
                if 'username' in self.proxy_config and 'password' in self.proxy_config:
                    return (
                        scheme,
                        hostname,
                        port,
                        self.proxy_config['username'],
                        self.proxy_config['password']
                    )
                else:
                    return (
                        scheme,
                        hostname,
                        port
                    )
            # Telethon只支持http代理，不支持https
            elif scheme == 'https':
                scheme = 'http'  # Telethon不支持https代理
            
            # 对于HTTP代理，如果需要认证，需要特殊处理
            if 'username' in self.proxy_config and 'password' in self.proxy_config:
                # Telethon的HTTP代理认证需要通过URL格式传递
                # 这种情况下我们返回基本配置，认证在客户端初始化时处理
                return (
                    scheme,
                    hostname,
                    port
                )
            else:
                return (
                    scheme,
                    hostname,
                    port
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
                # 检查是否是带认证的HTTP代理
                if (len(telethon_proxy) >= 3 and 
                    telethon_proxy[0] in ['http', 'https'] and 
                    settings.TELEGRAM_PROXY_USERNAME and 
                    settings.TELEGRAM_PROXY_PASSWORD):
                    # 对于HTTP代理认证，Telethon需要特殊处理
                    logger.info(f"使用带认证的HTTP代理: {telethon_proxy[0]}://{settings.TELEGRAM_PROXY_USERNAME}:****@{telethon_proxy[1]}:{telethon_proxy[2]}")
                    self.bot = TelegramClient(
                        'bot', 
                        settings.API_ID, 
                        settings.API_HASH,
                        proxy=(telethon_proxy[0], telethon_proxy[1], telethon_proxy[2])
                    )
                else:
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
                pyrogram_proxy_config = self._create_pyrogram_proxy_config(pyrogram_proxy)
                if pyrogram_proxy_config:
                    logger.info(f"使用代理: {pyrogram_proxy_config['scheme']}://{pyrogram_proxy_config.get('username', '')}@{pyrogram_proxy_config['hostname']}:{pyrogram_proxy_config['port']}")
                self.pyrogram_bot = Client(
                    "SaveRestricted",
                    bot_token=settings.BOT_TOKEN,
                    api_id=settings.API_ID,
                    api_hash=settings.API_HASH,
                    proxy=pyrogram_proxy_config
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
            # 保存原始SESSION配置
            original_session = settings.SESSION
            fallback_to_db = False
            
            # 如果没有设置SESSION，尝试从会话服务获取SESSION
            if not settings.SESSION:
                user_session = await self.session_svc.get_session(settings.AUTH)
                if user_session:
                    settings.SESSION = user_session
                    logger.info("从会话服务加载SESSION成功")
            
            if settings.SESSION:
                # 验证SESSION格式并获取修正后的值
                corrected_session = self._validate_and_fix_session(settings.SESSION)
                
                # 如果SESSION验证失败，记录错误并跳过Userbot初始化
                if corrected_session is None:
                    logger.error("SESSION验证失败，Userbot将不启动")
                    self.userbot = None
                    return
                
                # 只在SESSION被修正时更新配置
                if corrected_session != settings.SESSION:
                    settings.SESSION = corrected_session
                    logger.info("SESSION已自动修复")
                
                # 掩码敏感信息用于日志
                masked_session = security_manager.mask_sensitive_data(settings.SESSION, 15)
                logger.info(f"正在启动Userbot客户端 (Session: {masked_session})")
                
                # 获取代理配置
                pyrogram_proxy = self._get_pyrogram_proxy()
                
                # 创建Pyrogram客户端（Userbot）
                if pyrogram_proxy:
                    pyrogram_proxy_config = self._create_pyrogram_proxy_config(pyrogram_proxy)
                    if pyrogram_proxy_config:
                        logger.info(f"Userbot使用代理: {pyrogram_proxy_config['scheme']}://{pyrogram_proxy_config.get('username', '')}@{pyrogram_proxy_config['hostname']}:{pyrogram_proxy_config['port']}")
                    self.userbot = Client(
                        "saverestricted", 
                        session_string=settings.SESSION, 
                        api_hash=settings.API_HASH, 
                        api_id=settings.API_ID,
                        proxy=pyrogram_proxy_config
                    )
                else:
                    self.userbot = Client(
                        "saverestricted", 
                        session_string=settings.SESSION, 
                        api_hash=settings.API_HASH, 
                        api_id=settings.API_ID
                    )
                
                # 尝试启动Userbot
                try:
                    await self.userbot.start()
                    logger.info("Userbot客户端启动成功")
                except Exception as start_error:
                    error_msg = str(start_error).lower()
                    logger.error(f"Userbot启动失败: {start_error}")
                    
                    # 检查是否是SESSION相关错误
                    session_errors = ["unpack requires a buffer", "invalid session", "session expired", "session revoked", "session invalid"]
                    is_session_error = any(err in error_msg for err in session_errors)
                    
                    # 如果是SESSION错误或使用.env中的SESSION且启动失败，尝试从数据库获取SESSION
                    if is_session_error or (original_session and original_session == settings.SESSION):
                        logger.info("尝试从数据库获取备用SESSION...")
                        db_session = await self.session_svc.get_session(settings.AUTH)
                        if db_session and db_session != settings.SESSION:
                            logger.info("切换到数据库中的SESSION")
                            # 停止当前尝试
                            if self.userbot:
                                try:
                                    await self.userbot.stop()
                                except:
                                    pass
                                self.userbot = None
                            
                            # 使用数据库中的SESSION
                            settings.SESSION = db_session
                            fallback_to_db = True
                            
                            # 重新创建客户端
                            if pyrogram_proxy:
                                pyrogram_proxy_config = self._create_pyrogram_proxy_config(pyrogram_proxy)
                                self.userbot = Client(
                                    "saverestricted", 
                                    session_string=settings.SESSION, 
                                    api_hash=settings.API_HASH, 
                                    api_id=settings.API_ID,
                                    proxy=pyrogram_proxy_config
                                )
                            else:
                                self.userbot = Client(
                                    "saverestricted", 
                                    session_string=settings.SESSION, 
                                    api_hash=settings.API_HASH, 
                                    api_id=settings.API_ID
                                )
                            
                            # 再次尝试启动
                            try:
                                await self.userbot.start()
                                logger.info("使用数据库SESSION启动Userbot客户端成功")
                            except Exception as db_start_error:
                                logger.error(f"使用数据库SESSION启动Userbot客户端失败: {db_start_error}")
                                self.userbot = None
                                return
                        else:
                            # 没有备用SESSION可用或SESSION相同
                            self.userbot = None
                            return
                    else:
                        # 其他情况直接抛出错误
                        self.userbot = None
                        return
            else:
                logger.warning("未配置SESSION，Userbot将以有限功能运行")
                self.userbot = None
        except Exception as e:
            logger.error(f"Userbot启动失败: {e}")
            self.userbot = None
    
    def _validate_and_fix_session(self, session_string: str) -> Optional[str]:
        """验证SESSION格式并返回修正后的SESSION
        
        Args:
            session_string: 原始SESSION字符串
            
        Returns:
            修正后的SESSION字符串，如果验证失败则返回None
        """
        if not session_string:
            return None
        
        # 对于Pyrogram SESSION，直接返回原字符串（不做严格验证）
        # Pyrogram SESSION格式与Telethon不同，可能包含特殊字符
        if session_string.startswith(("1", "2", "3")):
            self.logger.info("检测到Pyrogram SESSION格式，跳过严格验证")
            return session_string
        
        # 对于其他SESSION，至少需要10个字符
        if len(session_string) < 10:
            self.logger.warning(f"SESSION长度不足: {len(session_string)} 字符")
            return None
        
        try:
            # 清理字符串，移除所有非base64字符
            import re
            cleaned_session = re.sub(r'[^A-Za-z0-9+/=_-]', '', session_string)
            
            # URL-safe base64 转换为标准 base64
            cleaned_session = cleaned_session.replace('-', '+').replace('_', '/')
            
            # 移除已有的等号，重新计算填充
            cleaned_session = cleaned_session.rstrip('=')
            
            # 自动添加正确的填充（Base64长度必须是4的倍数）
            padding_needed = (4 - len(cleaned_session) % 4) % 4
            if padding_needed > 0:
                cleaned_session += '=' * padding_needed
                self.logger.info(f"SESSION已自动修复填充，添加了{padding_needed}个等号")
            
            # 验证是否符合Base64模式
            if not re.match(r'^[A-Za-z0-9+/]*={0,2}$', cleaned_session):
                self.logger.warning(f"SESSION不符合Base64模式: {cleaned_session[:50]}...")
                return None
            
            # 尝试解码以验证格式
            import base64
            base64.b64decode(cleaned_session)
            self.logger.info("SESSION验证通过")
            return cleaned_session
        except Exception as e:
            self.logger.warning(f"SESSION验证失败: {e}")
            return None
    
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
            corrected_session = self._validate_and_fix_session(new_session)
            # 如果SESSION验证失败，记录错误并继续使用原始SESSION
            if corrected_session is None:
                logger.warning("SESSION验证失败，将使用原始SESSION尝试初始化")
                corrected_session = new_session
            
            # 停止当前userbot
            if self.userbot:
                try:
                    await self.userbot.stop()
                except:
                    pass
            
            # 更新配置
            settings.SESSION = corrected_session
            
            # 重新初始化userbot
            await self._init_userbot()
            
            logger.info("Userbot SESSION刷新成功")
            return self.userbot is not None and self.userbot.is_connected
        except Exception as e:
            logger.error(f"刷新Userbot SESSION时出错: {e}")
            # 即使出错也尝试使用原始SESSION初始化
            try:
                settings.SESSION = new_session
                await self._init_userbot()
                logger.info("Userbot SESSION使用原始字符串刷新成功")
                return self.userbot is not None and self.userbot.is_connected
            except Exception as fallback_error:
                logger.error(f"使用原始SESSION刷新也失败: {fallback_error}")
                # 最后的备用方案：尝试使用数据库中的SESSION
                try:
                    db_session = await self.session_svc.get_session(settings.AUTH)
                    if db_session and db_session != new_session:
                        logger.info("尝试使用数据库中的SESSION作为最后备用方案")
                        settings.SESSION = db_session
                        await self._init_userbot()
                        logger.info("使用数据库SESSION刷新Userbot成功")
                        return self.userbot is not None and self.userbot.is_connected
                except Exception as last_fallback_error:
                    logger.error(f"使用数据库SESSION作为备用方案也失败: {last_fallback_error}")
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