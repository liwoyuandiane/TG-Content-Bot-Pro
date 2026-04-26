"""会话管理插件"""

import asyncio
import logging
import re
import time
from typing import Dict, Any, Optional, List

from telethon import Button, events
from telethon.tl.types import User
from pyrogram import Client

from ..core.base_plugin import BasePlugin
from ..services.permission_service import permission_service
from ..services.user_service import user_service
from ..services.session_service import session_service
from ..utils.session_utils import validate_pyrogram_session, get_session_info
from ..core.clients import client_manager
from ..config import settings

logger = logging.getLogger(__name__)


class SessionPlugin(BasePlugin):
    """会话管理插件"""
    
    def __init__(self):
        super().__init__("session")
        self.session_generation_tasks: Dict[int, Dict[str, Any]] = {}
        self.CODE_TIMEOUT = 180
    
    async def on_load(self):
        """插件加载时注册事件处理器"""
        # 注册命令处理器 - 使用更精确的匹配
        client_manager.bot.add_event_handler(self._add_session, events.NewMessage(
            incoming=True, pattern=r'^/addsession\b'))
        client_manager.bot.add_event_handler(self._delete_session, events.NewMessage(
            incoming=True, pattern=r'^/delsession\b'))
        client_manager.bot.add_event_handler(self._list_sessions, events.NewMessage(
            incoming=True, pattern=r'^/sessions\b'))
        client_manager.bot.add_event_handler(self._view_session_callback, events.CallbackQuery(
            pattern=rb"view_session:\d+"))
        client_manager.bot.add_event_handler(self._my_session, events.NewMessage(
            incoming=True, pattern=r'^/mysession\b'))
        client_manager.bot.add_event_handler(self._generate_session, events.NewMessage(
            incoming=True, pattern=r'^/generatesession\b'))
        client_manager.bot.add_event_handler(self._cancel_session, events.NewMessage(
            incoming=True, pattern=r'^/cancelsession\b'))
        client_manager.bot.add_event_handler(self._retry_session, events.NewMessage(
            incoming=True, pattern=r'^/retry_session\b'))
        client_manager.bot.add_event_handler(self._handle_text_input, events.NewMessage(
            incoming=True, func=lambda e: e.text and not e.text.startswith('/')))
        
        self.logger.info("会话管理插件事件处理器已注册")
    
    async def on_unload(self):
        """插件卸载时移除事件处理器"""
        # 移除事件处理器 - 使用更精确的匹配
        client_manager.bot.remove_event_handler(self._add_session, events.NewMessage(
            incoming=True, pattern=r'^/addsession\b'))
        client_manager.bot.remove_event_handler(self._delete_session, events.NewMessage(
            incoming=True, pattern=r'^/delsession\b'))
        client_manager.bot.remove_event_handler(self._list_sessions, events.NewMessage(
            incoming=True, pattern=r'^/sessions\b'))
        client_manager.bot.remove_event_handler(self._view_session_callback, events.CallbackQuery(
            pattern=rb"view_session:\d+"))
        client_manager.bot.remove_event_handler(self._my_session, events.NewMessage(
            incoming=True, pattern=r'^/mysession\b'))
        client_manager.bot.remove_event_handler(self._generate_session, events.NewMessage(
            incoming=True, pattern=r'^/generatesession\b'))
        client_manager.bot.remove_event_handler(self._cancel_session, events.NewMessage(
            incoming=True, pattern=r'^/cancelsession\b'))
        client_manager.bot.remove_event_handler(self._retry_session, events.NewMessage(
            incoming=True, pattern=r'^/retry_session\b'))
        client_manager.bot.remove_event_handler(self._handle_text_input, events.NewMessage(
            incoming=True, func=lambda e: e.text and not e.text.startswith('/')))
        
        self.logger.info("会话管理插件事件处理器已移除")
    
    def get_help_text(self):
        """获取插件帮助文本"""
        return "会话管理功能，包括添加、删除、查看SESSION等操作"
    
    def _validate_session_string(self, session_string):
        """验证 SESSION 字符串格式 - 优化版本"""
        if not session_string:
            return False, "SESSION字符串不能为空"
        
        # 检查是否可能是手机号码（以+开头且长度较短）
        if session_string.startswith('+') and len(session_string) < 20:
            return False, "这看起来像是手机号码，请在SESSION生成流程中使用"
        
        # 对于Pyrogram SESSION格式（以1、2、3开头），使用专业验证
        if session_string.startswith(('1', '2', '3')):
            if validate_pyrogram_session(session_string):
                return True, "有效的Pyrogram SESSION格式"
            else:
                return False, f"Pyrogram SESSION格式无效，长度: {len(session_string)} 字符"
        
        # 对于其他SESSION格式，检查基本长度
        if len(session_string) >= 50:
            return True, "有效的SESSION格式"
        
        return False, f"SESSION字符串长度不足: {len(session_string)} 字符（最小50字符）"
    
    async def _add_session(self, event):
        """添加 SESSION 字符串"""
        try:
            # 权限检查：只允许授权用户使用
            if not await permission_service.require_authorized(event.sender_id):
                await event.reply("❌ 您没有权限使用此命令")
                return
            
            text = event.text.strip()
            
            # 检查是否是直接跟在命令后面的 SESSION 字符串
            if len(text.split(maxsplit=1)) >= 2:
                session_string = text.split(maxsplit=1)[1].strip()
            else:
                # 如果没有直接提供，启动一个对话来获取 SESSION 字符串
                async with client_manager.bot.conversation(event.chat_id) as conv:
                    await conv.send_message(
                        "**请输入 SESSION 字符串**\n\n"
                        "请直接发送您的 SESSION 字符串，我会自动处理其中可能包含的换行符和空格。\n\n"
                        "提示：您可以通过运行 /generatesession 命令在线生成 SESSION 字符串，或通过运行 get_session.py 脚本获取 SESSION 字符串。"
                    )
                    try:
                        response = await conv.get_response(timeout=120)
                        session_string = response.text.strip()
                        # 检查用户是否发送了命令而不是SESSION字符串
                        if session_string.startswith('/'):
                            await conv.send_message("❌ 检测到您发送的是命令而不是 SESSION 字符串。\n请重新使用 /addsession 命令并提供有效的 SESSION 字符串。")
                            return
                    except asyncio.TimeoutError:
                        await conv.send_message("⏱️ 等待响应超时，请重新使用 /addsession 命令。")
                        return
                    except Exception as e:
                        await conv.send_message(f"❌ 获取 SESSION 字符串时出错: {str(e)}")
                        return
            
            # 验证 SESSION 字符串
            is_valid, message = self._validate_session_string(session_string)
            if not is_valid:
                await event.reply(f"❌ {message}\n\n请确保您发送的是有效的 SESSION 字符串。")
                return
            
            # 对于Pyrogram v2，我们几乎不做清理，只做基本处理
            cleaned_session = session_string.strip() if session_string else session_string
            
            # 添加用户
            user = await event.get_sender()
            await user_service.add_user(
                user_id=event.sender_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            # 保存 SESSION
            success = await session_service.save_session(event.sender_id, cleaned_session)
            if success:
                # 更新全局配置中的SESSION
                settings.SESSION = cleaned_session
                
                # 尝试动态刷新 userbot SESSION
                try:
                    refresh_success = await client_manager.refresh_userbot_session(cleaned_session)
                    if refresh_success:
                        await event.reply(
                            "✅ SESSION 已保存并生效\n\n"
                            "Userbot 客户端已自动更新并启动成功\n"
                            "使用 /sessions 查看所有会话"
                        )
                    else:
                        # 即使刷新失败，也给用户一个重试的机会
                        await event.reply(
                            "✅ SESSION 已保存，但Userbot客户端启动失败\n\n"
                            "请尝试以下解决方案：\n"
                            "1. 检查SESSION是否有效\n"
                            "2. 使用 /retry_session 命令重试启动\n"
                            "3. 重启机器人\n"
                            "使用 /sessions 查看所有会话"
                        )
                except Exception as refresh_error:
                    self.logger.error(f"动态刷新 SESSION 失败: {refresh_error}")
                    await event.reply(
                        "✅ SESSION 已保存，但Userbot客户端刷新时出错\n\n"
                        f"错误信息: {str(refresh_error)}\n"
                        "请尝试以下解决方案：\n"
                        "1. 检查SESSION是否有效\n"
                        "2. 使用 /retry_session 命令重试启动\n"
                        "3. 重启机器人\n"
                        "使用 /sessions 查看所有会话"
                    )
            else:
                await event.reply("❌ 保存失败，请稍后重试")
        
        except Exception as e:
            await event.reply(f"❌ 添加失败: {str(e)}")
    
    async def _delete_session(self, event):
        """删除 SESSION 字符串（支持 /delsession <user_id|索引|me>）"""
        try:
            # 权限检查：只允许所有者使用
            if not await permission_service.require_owner(event.sender_id):
                await event.reply("❌ 此命令仅限所有者使用")
                return
            
            text = event.text.strip()
            parts = text.split(maxsplit=1)
            target_user_id = event.sender_id
            target_from_index = False

            if len(parts) == 2:
                arg = parts[1].strip()
                if arg.lower() in ("me", "self"):
                    target_user_id = event.sender_id
                elif arg.isdigit():
                    # 数字参数：优先按索引解析（1-based），否则按 user_id 解析
                    idx_or_id = int(arg)
                    sessions = await session_service.get_all_sessions()
                    if 1 <= idx_or_id <= len(sessions):
                        target_user_id = sessions[idx_or_id - 1].get("user_id")
                        target_from_index = True
                    else:
                        target_user_id = idx_or_id
                else:
                    await event.reply("❌ 参数无效，请使用 /delsession <索引|用户ID|me>")
                    return
            else:
                # 没有参数，显示帮助信息
                await event.reply(
                    "🗑️ **删除 SESSION**\n\n"
                    "用法: `/delsession <参数>`\n\n"
                    "参数:\n"
                    "  • `me` - 删除自己的 SESSION\n"
                    "  • `<user_id>` - 删除指定用户的 SESSION\n"
                    "  • `<索引>` - 删除指定索引的 SESSION\n\n"
                    "示例:\n"
                    "  `/delsession me`\n"
                    "  `/delsession 123456789`\n"
                    "  `/delsession 1`\n\n"
                    "⚠️ 注意: 删除 SESSION 后，该用户将无法访问私有频道"
                )
                return

            success = await session_service.delete_session(target_user_id)
            if success:
                # 若删除的是自己的 SESSION，则尝试停止当前 userbot
                if target_user_id == event.sender_id:
                    try:
                        if client_manager.userbot:
                            await client_manager.userbot.stop()
                            client_manager.userbot = None
                            # 更新全局配置中的SESSION
                            settings.SESSION = None
                    except Exception as refresh_error:
                        self.logger.error(f"动态刷新 SESSION 失败: {refresh_error}")
                await event.reply(f"✅ 已删除用户 {target_user_id} 的 SESSION")
            else:
                await event.reply("❌ 删除失败或 SESSION 不存在")

        except Exception as e:
            await event.reply(f"❌ 删除失败: {str(e)}")
    
    async def _list_sessions(self, event):
        """列出所有 SESSION"""
        try:
            # 权限检查：只允许所有者使用
            if not await permission_service.require_owner(event.sender_id):
                await event.reply("❌ 此命令仅限所有者使用")
                return
            
            sessions = await session_service.get_all_sessions()
            
            if not sessions:
                await event.reply("📭 暂无保存的 SESSION")
                return
            
            msg = "📋 **已保存的 SESSION 列表**\n\n"
            encryption_enabled = session_service.cipher_suite is not None
            buttons = []
            for i, user in enumerate(sessions, 1):
                user_id = user.get("user_id")
                username = user.get("username", "未知")
                session = user.get("session_string", "")
                session_preview = session[:20] + "..." if len(session) > 20 else session
                
                msg += f"{i}. **用户**: {username} ({user_id})\n"
                msg += f"   SESSION: {session_preview}\n"
                msg += f"   👉 点击下方按钮查看完整SESSION\n\n"
                buttons.append([Button.inline(f"查看 {i}", data=f"view_session:{user_id}")])
            
            msg += f"**总计**: {len(sessions)} 个会话\n\n"
            if not encryption_enabled:
                msg += "⚠️ 当前未配置加密密钥，SESSION可能显示为乱码。\n"
                msg += "   • 在 .env 中设置 ENCRYPTION_KEY 可启用解密显示\n"
                msg += "   • 查看数据库：直接在 MongoDB 中查看 users/sessions 集合\n"
                msg += "   • 删除失效SESSION：使用 /delsession <索引|用户ID|me>\n\n"
            msg += "🗑️ 删除用法：/delsession <索引|用户ID|me>\n"
            msg += "   例如：/delsession 1 或 /delsession 123456789 或 /delsession me"
            
            await event.reply(msg, buttons=buttons, parse_mode="markdown")
        
        except Exception as e:
            await event.reply(f"❌ 获取列表失败: {str(e)}")
    
    async def _my_session(self, event):
        """查看自己的 SESSION"""
        try:
            # 权限检查：只允许授权用户使用
            if not await permission_service.require_authorized(event.sender_id):
                await event.reply("❌ 您没有权限使用此命令")
                return
            
            session = await session_service.get_session(event.sender_id)
            
            if not session:
                await event.reply(
                    "❌ 您还没有保存 SESSION\n\n"
                    "使用 /addsession 添加"
                )
                return
            
            # 创建一个可以一键复制的格式
            msg = "🔐 **您的 SESSION 信息**\n\n"
            msg += f"用户ID: `{event.sender_id}`\n\n"
            
            # 添加SESSION详细信息
            session_info = get_session_info(session)
            if session_info:
                msg += "**SESSION详情**:\n"
                if "dc_id" in session_info:
                    msg += f"  DC ID: {session_info['dc_id']}\n"
                if "api_id" in session_info:
                    msg += f"  API ID: {session_info['api_id']}\n"
                if "user_id" in session_info:
                    msg += f"  用户ID: {session_info['user_id']}\n"
                if "is_bot" in session_info:
                    msg += f"  是否机器人: {'是' if session_info['is_bot'] else '否'}\n"
                msg += f"  长度: {session_info.get('length', len(session))} 字符\n"
                msg += f"  有效性: {'✅ 有效' if session_info.get('valid', False) else '❌ 无效'}\n\n"
            
            msg += "**SESSION**（点击下方文本即可全选复制）:\n"
            msg += f"||`{session}`||\n\n"  # 使用隐藏文本格式，点击即可全选
            msg += "👉 **使用方法**:\n"
            msg += "1️⃣ 点击上面的SESSION文本\n"
            msg += "2️⃣ 长按选择\"全选\"\n"
            msg += "3️⃣ 点击\"复制\"\n\n"
            msg += "⚠️ **安全提示**:\n"
            msg += "• 请勿泄露此信息给任何人\n"
            msg += "• SESSION可以完全控制您的账号\n"
            msg += "• 建议截图保存而不是复制文本"
            
            await event.reply(msg)
        
        except Exception as e:
            await event.reply(f"❌ 获取失败: {str(e)}")
    
    async def _generate_session(self, event):
        """在线生成 SESSION 字符串 - 优化版本"""
        try:
            # 权限检查：只允许授权用户使用
            if not await permission_service.require_authorized(event.sender_id):
                await event.reply("❌ 您没有权限使用此命令")
                return
            
            user_id = event.sender_id
            
            if user_id in self.session_generation_tasks:
                await event.reply("❌ 您已经有一个正在进行的 SESSION 生成任务\n\n使用 /cancelsession 取消")
                return
            
            # 检查环境变量中是否已有 API_ID 和 API_HASH
            has_api_credentials = bool(settings.API_ID) and bool(settings.API_HASH)
            
            # 参考开源项目，使用更友好的交互流程
            if has_api_credentials:
                await event.reply(
                    "🔐 **在线生成 SESSION**\n\n"
                    "✅ 检测到已配置的 API 凭证\n"
                    "📱 请发送您的 **手机号码**\n\n"
                    "💡 **格式示例**:\n"
                    "• +8613800138000 (中国)\n"
                    "• +919876543210 (印度)\n"
                    "• +1234567890 (美国)\n\n"
                    "⚠️ **重要提示**:\n"
                    "• 确保手机号码正确\n"
                    "• 确保手机可接收短信\n"
                    "• 使用 /cancelsession 可随时取消"
                )
                
                self.session_generation_tasks[user_id] = {
                    'step': 'phone',
                    'data': {
                        'api_id': settings.API_ID,
                        'api_hash': settings.API_HASH,
                        'start_time': time.time()
                    }
                }
            else:
                await event.reply(
                    "🔐 **在线生成 SESSION**\n\n"
                    "请按以下步骤操作：\n\n"
                    "1️⃣ **API_ID**\n"
                    "   • 从 my.telegram.org 获取\n"
                    "   • 格式: 纯数字 (如: 123456)\n\n"
                    "💡 **如何获取**:\n"
                    "• 登录 my.telegram.org\n"
                    "• 创建应用并获取 API 凭证\n"
                    "• 发送 API_ID 开始流程\n\n"
                    "⚠️ 使用 /cancelsession 可随时取消"
                )
        except Exception as e:
            await event.reply(f"❌ 启动生成失败: {str(e)}")
    
    async def _cancel_session(self, event):
        """取消 SESSION 生成"""
        user_id = event.sender_id
        
        if user_id not in self.session_generation_tasks:
            await event.reply("❌ 您没有正在进行的 SESSION 生成任务")
            return
        
        # 取消标记用户会话状态
        from .message_handler import message_handler_plugin
        message_handler_plugin.mark_user_in_conversation(user_id, False)
        
        del self.session_generation_tasks[user_id]
        await event.reply("✅ SESSION 生成任务已取消")
    
    async def _retry_session(self, event):
        """重试启动Userbot客户端"""
        try:
            await event.reply("⏳ 正在重试启动Userbot客户端...")
            
            # 从数据库获取SESSION
            session = await session_service.get_session(event.sender_id)
            if not session:
                await event.reply("❌ 未找到SESSION，请先使用 /addsession 添加")
                return
            
            # 更新全局配置中的SESSION
            settings.SESSION = session
            
            # 尝试刷新Userbot SESSION
            success = await client_manager.refresh_userbot_session(session)
            
            if success:
                await event.reply("✅ Userbot客户端启动成功！")
            else:
                await event.reply("❌ Userbot客户端启动失败\n\n请检查SESSION是否有效或尝试重启机器人")
                
        except Exception as e:
            self.logger.error(f"重试启动Userbot失败: {e}")
            await event.reply(f"❌ Userbot客户端启动失败\n\n请检查SESSION是否有效或尝试重启机器人")

    async def _view_session_callback(self, event):
        """查看完整SESSION回调处理"""
        try:
            # 权限检查：只允许所有者使用
            if not await permission_service.require_owner(event.sender_id):
                await event.answer("❌ 您没有权限查看SESSION", alert=True)
                return
            
            data = event.data.decode("utf-8", errors="ignore")
            # 解析格式: view_session:<user_id>
            parts = data.split(":", 1)
            if len(parts) != 2 or not parts[1].isdigit():
                await event.answer("参数无效", alert=True)
                return
            target_user_id = int(parts[1])
            session = await session_service.get_session(target_user_id)
            if not session:
                await event.answer("该用户未保存SESSION", alert=True)
                return
            encryption_enabled = session_service.cipher_suite is not None
            msg = "🔐 **完整SESSION**\n\n"
            msg += f"用户ID: `{target_user_id}`\n\n"
            msg += "||`" + session + "`||\n\n"
            if not encryption_enabled:
                msg += "⚠️ 未配置加密密钥，若显示乱码请在 .env 设置 ENCRYPTION_KEY 后重试。\n"
                msg += "• 删除失效SESSION：/delsession <索引|用户ID|me>\n"
            await event.client.send_message(event.chat_id, msg, parse_mode="markdown")
            await event.answer("已发送完整SESSION", alert=False)
        except Exception as e:
            await event.answer(f"出错: {str(e)}", alert=True)

    async def _handle_text_input(self, event):
        """处理文本输入,用于 SESSION 生成流程"""
        user_id = event.sender_id
        
        # 只处理在SESSION生成流程中的用户输入
        if user_id not in self.session_generation_tasks:
            return
            
        # 检查用户是否发送了其他命令，如果是则自动退出当前流程
        if event.text and event.text.startswith('/'):
            # 自动退出当前的SESSION生成流程
            if user_id in self.session_generation_tasks:
                task = self.session_generation_tasks[user_id]
                if 'client' in task.get('data', {}):
                    try:
                        await task['data']['client'].disconnect()
                    except:
                        pass
                del self.session_generation_tasks[user_id]
                
                # 取消标记用户会话状态
                from .message_handler import message_handler_plugin
                message_handler_plugin.mark_user_in_conversation(user_id, False)
                
                await event.reply("✅ 已退出 SESSION 生成流程，正在处理您的新命令...")
            return
            
        task = self.session_generation_tasks[user_id]
        step = task['step']
        data = task['data']
        
        try:
            # 检查任务是否超时
            if time.time() - data.get('start_time', 0) > self.CODE_TIMEOUT:
                del self.session_generation_tasks[user_id]
                from .message_handler import message_handler_plugin
                message_handler_plugin.mark_user_in_conversation(user_id, False)
                await event.reply("⏱️ SESSION生成任务已超时，请重新开始")
                return
            
            if step == 'phone':
                phone = event.text.strip()
                if not phone.startswith('+') or len(phone) < 10:
                    await event.reply("❌ 手机号码格式无效，请重新发送\n\n格式示例: +1234567890")
                    return
                
                # 创建临时客户端用于登录
                temp_client = Client(
                    "temp_session_gen",
                    api_id=data['api_id'],
                    api_hash=data['api_hash'],
                    app_version="Pyrogram 2.0.106",
                    device_model="Session Generator",
                    system_version="Linux 5.4",
                    lang_code="en"
                )
                
                await temp_client.connect()
                
                # 发送验证码
                sent_code = await temp_client.send_code(phone)
                await event.reply(
                    "⏳ 验证码已通过 Telegram 应用内消息发送\n\n"
                    "📱 验证码查找方法:\n"
                    "1️⃣ 查看 Telegram 通知栏\n"
                    "2️⃣ 在聊天列表顶部查找 \"Telegram\" 官方账号\n"
                    "3️⃣ 检查是否有验证码弹窗\n\n"
                    "❓ 看不到验证码？\n"
                    "• 发送 resend 切换为短信接收\n"
                    "• 或直接发送验证码: 1 2 3 4 5\n\n"
                    f"⏱ 下一种方式: {sent_code.type.name}"
                )
                
                # 更新任务状态
                task['step'] = 'code'
                task['data'].update({
                    'client': temp_client,
                    'phone': phone,
                    'phone_code_hash': sent_code.phone_code_hash
                })
                
            elif step == 'code':
                code_text = event.text.strip()
                
                # 处理重新发送验证码请求
                if code_text.lower() == 'resend':
                    try:
                        sent_code = await data['client'].resend_code(data['phone'], data['phone_code_hash'])
                        await event.reply(
                            "🔁 验证码已重新发送\n\n"
                            f"⏱ 下一种方式: {sent_code.type.name}"
                        )
                        task['data']['phone_code_hash'] = sent_code.phone_code_hash
                    except Exception as e:
                        await event.reply(f"❌ 重新发送验证码失败: {str(e)}")
                    return
                
                # 处理验证码输入
                try:
                    # 分割验证码（支持空格分隔的格式）
                    code = ''.join(code_text.split())
                    if not code.isdigit():
                        await event.reply("❌ 验证码只能包含数字，请重新发送")
                        return
                    
                    # 签入客户端
                    await data['client'].sign_in(data['phone'], data['phone_code_hash'], code)
                    
                    # 登录成功，生成SESSION
                    session_string = await data['client'].export_session_string()
                    await data['client'].disconnect()
                    
                    # 取消标记用户会话状态
                    from .message_handler import message_handler_plugin
                    message_handler_plugin.mark_user_in_conversation(user_id, False)
                    
                    del self.session_generation_tasks[user_id]
                    
                    # 保存SESSION
                    success = await session_service.save_session(user_id, session_string)
                    
                    if success:
                        # 更新全局配置中的SESSION
                        settings.SESSION = session_string
                        
                        # 尝试刷新userbot
                        try:
                            refresh_success = await client_manager.refresh_userbot_session(session_string)
                            
                            if refresh_success:
                                await event.reply(
                                    "✅ SESSION 生成成功！\n\n"
                                    "SESSION 已自动保存到数据库并生效\n"
                                    "Userbot客户端已启动成功\n\n"
                                    "🔐 使用 /mysession 查看您的 SESSION"
                                )
                            else:
                                await event.reply(
                                    "✅ SESSION 生成成功！\n\n"
                                    "SESSION 已自动保存到数据库\n"
                                    "但Userbot客户端启动失败，请使用 /retry_session 重试或重启机器人\n\n"
                                    "🔐 使用 /mysession 查看您的 SESSION"
                                )
                        except Exception as refresh_error:
                            self.logger.error(f"刷新Userbot SESSION失败: {refresh_error}")
                            await event.reply(
                                "✅ SESSION 生成成功！\n\n"
                                "SESSION 已自动保存到数据库\n"
                                f"但刷新Userbot时出错: {str(refresh_error)}\n"
                                "请使用 /retry_session 重试或重启机器人\n\n"
                                "🔐 使用 /mysession 查看您的 SESSION"
                            )
                    else:
                        await event.reply("❌ SESSION保存失败，请稍后重试")

                except Exception as e:
                    err_str = str(e).lower()
                    if "password" in err_str or "two" in err_str:
                        # 需要两步验证密码
                        await event.reply(
                            "🔐 检测到两步验证\n\n"
                            "请发送您的两步验证密码"
                        )
                        task['step'] = 'password'
                    elif "code" in err_str or "invalid" in err_str:
                        await event.reply("❌ 验证码错误，请重新发送")
                    else:
                        error_msg = f"❌ 验证失败: {err_str}\n\n请使用 /generatesession 重新开始"
                        await data['client'].disconnect()
                        del self.session_generation_tasks[user_id]
                        await event.reply(error_msg)
                        return
                        
            elif step == 'password':
                password = event.text.strip()
                if not password:
                    await event.reply("❌ 密码不能为空，请重新发送")
                    return
                
                try:
                    await event.reply("⏳ 正在验证两步验证密码...")
                    await data['client'].check_password(password)
                except Exception as pwd_error:
                    await event.reply(f"❌ 两步验证密码错误: {str(pwd_error)}\n\n请重新发送密码")
                    return
                
                # 密码验证成功，继续生成SESSION
                session_string = await data['client'].export_session_string()
                
                await data['client'].disconnect()
                
                # 取消标记用户会话状态
                from .message_handler import message_handler_plugin
                message_handler_plugin.mark_user_in_conversation(user_id, False)
                
                del self.session_generation_tasks[user_id]
                
                # 更新全局配置中的SESSION
                settings.SESSION = session_string
                
                success = await session_service.save_session(user_id, session_string)
                
                if success:
                    # 尝试动态刷新 userbot SESSION
                    try:
                        refresh_success = await client_manager.refresh_userbot_session(session_string)
                        
                        if refresh_success:
                            await event.reply(
                                "✅ SESSION 生成成功！\n\n"
                                "SESSION 已自动保存到数据库并生效\n"
                                "Userbot客户端已启动成功\n\n"
                                "🔐 使用 /mysession 查看您的 SESSION"
                            )
                        else:
                            await event.reply(
                                "✅ SESSION 生成成功！\n\n"
                                "SESSION 已自动保存到数据库\n"
                                "但Userbot客户端启动失败，请使用 /retry_session 重试或重启机器人\n\n"
                                "🔐 使用 /mysession 查看您的 SESSION"
                            )
                    except Exception as refresh_error:
                        self.logger.error(f"刷新Userbot SESSION失败: {refresh_error}")
                        await event.reply(
                            "✅ SESSION 生成成功！\n\n"
                            "SESSION 已自动保存到数据库\n"
                            f"但刷新Userbot时出错: {str(refresh_error)}\n"
                            "请使用 /retry_session 重试或重启机器人\n\n"
                            "🔐 使用 /mysession 查看您的 SESSION"
                        )
                else:
                    await event.reply("❌ SESSION保存失败，请稍后重试")
                    
        except Exception as e:
            self.logger.error(f"处理SESSION生成输入时出错: {e}", exc_info=True)
            await event.reply(f"❌ 处理过程中发生错误: {str(e)}\n\n请使用 /generatesession 重新开始")
            
            # 清理任务
            if user_id in self.session_generation_tasks:
                task = self.session_generation_tasks[user_id]
                if 'client' in task.get('data', {}):
                    try:
                        await task['data']['client'].disconnect()
                    except:
                        pass
                del self.session_generation_tasks[user_id]
                
            # 取消标记用户会话状态
            from .message_handler import message_handler_plugin
            message_handler_plugin.mark_user_in_conversation(user_id, False)


# 创建插件实例并注册
session_plugin = SessionPlugin()

# 注册到插件注册表
from ..core.base_plugin import plugin_registry
plugin_registry.register(session_plugin)