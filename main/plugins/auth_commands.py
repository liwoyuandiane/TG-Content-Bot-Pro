"""授权管理插件"""
import logging
from typing import List

from ..core.base_plugin import BasePlugin
from ..core.clients import client_manager
from ..config import settings
from ..services.user_service import user_service

from telethon import events

logger = logging.getLogger(__name__)


class AuthPlugin(BasePlugin):
    """授权管理插件"""
    
    def __init__(self):
        super().__init__("auth")
    
    async def on_load(self):
        """插件加载时注册事件处理器"""
        # 注册命令处理器
        client_manager.bot.add_event_handler(self._authorize_user, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern="/authorize"))
        client_manager.bot.add_event_handler(self._unauthorize_user, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern="/unauthorize"))
        client_manager.bot.add_event_handler(self._list_authorized_users, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern="/authorized"))
        
        self.logger.info("授权管理插件事件处理器已注册")
    
    async def on_unload(self):
        """插件卸载时移除事件处理器"""
        # 移除事件处理器
        client_manager.bot.remove_event_handler(self._authorize_user, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern="/authorize"))
        client_manager.bot.remove_event_handler(self._unauthorize_user, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern="/unauthorize"))
        client_manager.bot.remove_event_handler(self._list_authorized_users, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern="/authorized"))
        
        self.logger.info("授权管理插件事件处理器已移除")
    
    async def _authorize_user(self, event):
        """授权用户命令"""
        try:
            text = event.text.strip()
            
            if len(text.split()) < 2:
                await event.reply(
                    "**授权用户**\n\n"
                    "用法:\n"
                    "  /authorize <user_id>\n\n"
                    "示例:\n"
                    "  /authorize 123456789\n\n"
                    "请提供要授权的用户ID"
                )
                return
            
            # 解析用户ID
            try:
                user_id = int(text.split()[1])
            except ValueError:
                await event.reply("❌ 用户ID必须是数字")
                return
            
            # 不能授权主用户（已经在环境变量中）
            if user_id in settings.get_auth_users():
                await event.reply("❌ 该用户已经是主授权用户")
                return
            
            # 授权用户
            success = await user_service.authorize_user(user_id)
            if success:
                await event.reply(f"✅ 用户 {user_id} 已授权")
            else:
                # 检查用户是否存在
                user = await user_service.get_user(user_id)
                if user:
                    await event.reply(f"✅ 用户 {user_id} 已经是授权用户")
                else:
                    # 添加用户并授权
                    await user_service.add_user(user_id, is_authorized=True)
                    await event.reply(f"✅ 用户 {user_id} 已添加并授权")
        
        except Exception as e:
            await event.reply(f"❌ 授权失败: {str(e)}")
    
    async def _unauthorize_user(self, event):
        """取消用户授权命令"""
        try:
            text = event.text.strip()
            
            if len(text.split()) < 2:
                await event.reply(
                    "**取消用户授权**\n\n"
                    "用法:\n"
                    "  /unauthorize <user_id>\n\n"
                    "示例:\n"
                    "  /unauthorize 123456789\n\n"
                    "请提供要取消授权的用户ID"
                )
                return
            
            # 解析用户ID
            try:
                user_id = int(text.split()[1])
            except ValueError:
                await event.reply("❌ 用户ID必须是数字")
                return
            
            # 不能取消主用户的授权
            if user_id in settings.get_auth_users():
                await event.reply("❌ 不能取消主用户的授权")
                return
            
            # 取消用户授权
            success = await user_service.unauthorize_user(user_id)
            if success:
                await event.reply(f"✅ 用户 {user_id} 已取消授权")
            else:
                # 检查用户是否存在
                user = await user_service.get_user(user_id)
                if user:
                    await event.reply(f"❌ 用户 {user_id} 未被授权")
                else:
                    await event.reply(f"❌ 用户 {user_id} 不存在")
        
        except Exception as e:
            await event.reply(f"❌ 取消授权失败: {str(e)}")
    
    async def _list_authorized_users(self, event):
        """列出所有授权用户命令"""
        try:
            # 获取主用户和数据库中的授权用户
            main_users = settings.get_auth_users()
            db_authorized = await user_service.get_authorized_users()
            
            # 合并并去重
            all_authorized = list(set(main_users + db_authorized))
            
            if not all_authorized:
                await event.reply("📭 暂无授权用户")
                return
            
            msg = "📋 **授权用户列表**\n\n"
            msg += "**主授权用户** (环境变量):\n"
            for user_id in main_users:
                msg += f"• {user_id}\n"
            
            if db_authorized:
                msg += "\n**数据库授权用户**:\n"
                for user_id in db_authorized:
                    msg += f"• {user_id}\n"
            
            msg += f"\n**总计**: {len(all_authorized)} 个授权用户"
            
            await event.reply(msg)
        
        except Exception as e:
            await event.reply(f"❌ 获取授权用户列表失败: {str(e)}")


# 创建插件实例并注册
auth_plugin = AuthPlugin()

# 注册到插件注册表
from ..core.base_plugin import plugin_registry
plugin_registry.register(auth_plugin)