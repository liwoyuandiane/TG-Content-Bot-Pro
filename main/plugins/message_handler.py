"""消息链接处理插件"""
import logging
from telethon import events

from ..core.base_plugin import BasePlugin
from ..core.clients import client_manager
from ..config import settings
from ..services.download_service import download_service
from ..services.user_service import user_service
from ..utils.media_utils import get_link


logger = logging.getLogger(__name__)


class MessageHandlerPlugin(BasePlugin):
    """消息链接处理插件"""
    
    def __init__(self):
        super().__init__("message_handler")
    
    async def on_load(self):
        """插件加载时注册事件处理器"""
        # 注册普通文本消息处理器（不以 / 开头的消息）
        client_manager.bot.add_event_handler(
            self._handle_message_link,
            events.NewMessage(incoming=True, func=lambda e: not e.text.startswith('/') if e.text else False)
        )
        
        self.logger.info("消息链接处理插件事件处理器已注册")
    
    async def on_unload(self):
        """插件卸载时移除事件处理器"""
        client_manager.bot.remove_event_handler(
            self._handle_message_link,
            events.NewMessage(incoming=True, func=lambda e: not e.text.startswith('/') if e.text else False)
        )
        
        self.logger.info("消息链接处理插件事件处理器已移除")
    
    async def _handle_message_link(self, event):
        """处理消息链接"""
        user_id = event.sender_id
        text = event.text.strip()
        
        # 检查用户是否授权
        if not await user_service.is_user_authorized(user_id):
            return
        
        # 检查是否包含 Telegram 链接
        if not any(domain in text.lower() for domain in ['t.me/', 'telegram.me/']):
            return
        
        # 提取链接
        try:
            link = get_link(text)
            if not link:
                await event.reply("❌ 未找到有效的 Telegram 消息链接")
                return
        except Exception as e:
            self.logger.error(f"解析链接失败: {e}")
            await event.reply("❌ 链接解析失败，请检查链接格式")
            return
        
        # 发送处理中消息
        status_msg = await event.reply("⏳ 正在处理...")
        
        try:
            # 调用下载服务处理消息
            success = await download_service.download_message(
                userbot=client_manager.userbot,
                client=client_manager.pyrogram_bot,
                telethon_bot=client_manager.bot,
                sender=user_id,
                edit_id=status_msg.id,
                msg_link=link,
                offset=0
            )
            
            if success:
                self.logger.info(f"用户 {user_id} 成功下载: {link}")
            else:
                self.logger.warning(f"用户 {user_id} 下载失败: {link}")
                
        except Exception as e:
            self.logger.error(f"处理消息链接时出错: {e}", exc_info=True)
            await status_msg.edit(f"❌ 处理失败: {str(e)}")


# 创建插件实例并注册
message_handler_plugin = MessageHandlerPlugin()

# 注册到插件注册表
from ..core.base_plugin import plugin_registry
plugin_registry.register(message_handler_plugin)
