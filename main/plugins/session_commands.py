"""会话管理插件"""
import re
from typing import List, Dict, Any

from ..core.base_plugin import BasePlugin
from ..core.clients import client_manager
from ..config import settings
from ..services.session_service import session_service
from ..services.user_service import user_service

from telethon import events

class SessionPlugin(BasePlugin):
    """会话管理插件"""
    
    def __init__(self):
        super().__init__("session")
    
    async def on_load(self):
        """插件加载时注册事件处理器"""
        # 注册命令处理器
        client_manager.bot.add_event_handler(self._add_session, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern="/addsession"))
        client_manager.bot.add_event_handler(self._delete_session, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern="/delsession"))
        client_manager.bot.add_event_handler(self._list_sessions, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern="/sessions"))
        client_manager.bot.add_event_handler(self._my_session, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern="/mysession"))
        
        self.logger.info("会话管理插件事件处理器已注册")
    
    async def on_unload(self):
        """插件卸载时移除事件处理器"""
        # 移除事件处理器
        client_manager.bot.remove_event_handler(self._add_session, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern="/addsession"))
        client_manager.bot.remove_event_handler(self._delete_session, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern="/delsession"))
        client_manager.bot.remove_event_handler(self._list_sessions, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern="/sessions"))
        client_manager.bot.remove_event_handler(self._my_session, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern="/mysession"))
        
        self.logger.info("会话管理插件事件处理器已移除")
    
    def _validate_session_string(self, session_string):
        """验证 SESSION 字符串格式"""
        if not session_string:
            return False, "SESSION字符串不能为空"
        
        # 基本格式检查（Pyrogram session 字符串通常是 base64 编码）
        if not re.match(r"^[A-Za-z0-9+/=]+$", session_string):
            return False, "SESSION字符串格式无效"
        
        # 长度检查
        if len(session_string) < 50:
            return False, "SESSION字符串长度不足"
        
        return True, "有效"
    
    async def _add_session(self, event):
        """添加 SESSION 字符串"""
        try:
            text = event.text.strip()
            
            if len(text.split(maxsplit=1)) < 2:
                await event.reply(
                    "**添加 SESSION 字符串**\n\n"
                    "用法:\n"
                    "  /addsession <session_string>\n\n"
                    "示例:\n"
                    "  /addsession abc123...xyz\n\n"
                    "获取 SESSION:\n"
                    "运行 get_session.py 脚本生成\n\n"
                    "请输入正确的 SESSION 字符串"
                )
                return
            
            session_string = text.split(maxsplit=1)[1].strip()
            
            # 验证 SESSION 字符串
            is_valid, message = self._validate_session_string(session_string)
            if not is_valid:
                await event.reply(f"❌ {message}")
                return
            
            # 添加用户
            user = await event.get_sender()
            await user_service.add_user(
                user_id=event.sender_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            # 保存 SESSION
            success = await session_service.save_session(event.sender_id, session_string)
            if success:
                await event.reply(
                    "✅ SESSION 已保存到 MongoDB\n\n"
                    "重启机器人后生效\n"
                    "使用 /sessions 查看所有会话"
                )
            else:
                await event.reply("❌ 保存失败，请稍后重试")
        
        except Exception as e:
            await event.reply(f"❌ 添加失败: {str(e)}")
    
    async def _delete_session(self, event):
        """删除 SESSION 字符串"""
        try:
            success = await session_service.delete_session(event.sender_id)
            if success:
                await event.reply("✅ SESSION 已删除\n\n重启机器人后生效")
            else:
                await event.reply("❌ 删除失败或 SESSION 不存在")
        except Exception as e:
            await event.reply(f"❌ 删除失败: {str(e)}")
    
    async def _list_sessions(self, event):
        """列出所有 SESSION"""
        try:
            sessions = await session_service.get_all_sessions()
            
            if not sessions:
                await event.reply("📭 暂无保存的 SESSION")
                return
            
            msg = "📋 **已保存的 SESSION 列表**\n\n"
            for i, user in enumerate(sessions, 1):
                user_id = user.get("user_id")
                username = user.get("username", "未知")
                session = user.get("session_string", "")
                session_preview = session[:20] + "..." if len(session) > 20 else session
                
                msg += f"{i}. **用户**: {username} ({user_id})\n"
                msg += f"   SESSION: \n\n"
            
            msg += f"**总计**: {len(sessions)} 个会话"
            
            await event.reply(msg)
        
        except Exception as e:
            await event.reply(f"❌ 获取列表失败: {str(e)}")
    
    async def _my_session(self, event):
        """查看自己的 SESSION"""
        try:
            session = await session_service.get_session(event.sender_id)
            
            if not session:
                await event.reply(
                    "❌ 您还没有保存 SESSION\n\n"
                    "使用  添加"
                )
                return
            
            msg = "🔐 **您的 SESSION 信息**\n\n"
            msg += f"用户ID: \n"
            msg += f"SESSION: \n\n"
            msg += "⚠️ 请勿泄露此信息"
            
            await event.reply(msg)
        
        except Exception as e:
            await event.reply(f"❌ 获取失败: {str(e)}")

# 创建插件实例并注册
session_plugin = SessionPlugin()

# 注册到插件注册表
from ..core.base_plugin import plugin_registry
plugin_registry.register(session_plugin)
