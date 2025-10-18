"""会话管理插件"""
import re
import asyncio
import time
from typing import List, Dict, Any, Optional
from pyrogram import Client

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
        self.session_generation_tasks: Dict[int, Dict[str, Any]] = {}
        self.CODE_TIMEOUT = 180
    
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
        client_manager.bot.add_event_handler(self._generate_session, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern="/generatesession"))
        client_manager.bot.add_event_handler(self._cancel_session, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern="/cancelsession"))
        client_manager.bot.add_event_handler(self._handle_text_input, events.NewMessage(
            incoming=True, from_users=settings.AUTH, func=lambda e: not e.text.startswith('/')))
        
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
        client_manager.bot.remove_event_handler(self._generate_session, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern="/generatesession"))
        client_manager.bot.remove_event_handler(self._cancel_session, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern="/cancelsession"))
        client_manager.bot.remove_event_handler(self._handle_text_input, events.NewMessage(
            incoming=True, from_users=settings.AUTH, func=lambda e: not e.text.startswith('/')))
        
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
    
    async def _generate_session(self, event):
        """在线生成 SESSION 字符串"""
        try:
            user_id = event.sender_id
            
            if user_id in self.session_generation_tasks:
                await event.reply("❌ 您已经有一个正在进行的 SESSION 生成任务\n\n使用 /cancelsession 取消")
                return
            
            # 检查环境变量中是否已有 API_ID 和 API_HASH
            has_api_credentials = bool(settings.API_ID) and bool(settings.API_HASH)
            
            if has_api_credentials:
                await event.reply(
                    "🔐 **在线生成 SESSION**\n\n"
                    "检测到已配置的 API 凭证，将直接使用。\n\n"
                    "请发送您的 **手机号码**\n"
                    "   (包含国家代码，例如：+8613800138000)\n\n"
                    "⚠️ 请确保手机号码正确，否则生成会失败\n"
                    "💡 使用 /cancelsession 可随时取消"
                )
                
                self.session_generation_tasks[user_id] = {
                    'step': 'phone',
                    'data': {
                        'api_id': settings.API_ID,
                        'api_hash': settings.API_HASH
                    }
                }
            else:
                await event.reply(
                    "🔐 **在线生成 SESSION**\n\n"
                    "请按以下步骤操作：\n\n"
                    "1️⃣ 请发送您的 **API_ID**\n"
                    "   (从 my.telegram.org 获取)\n\n"
                    "⚠️ 请确保信息准确，否则生成会失败\n"
                    "💡 使用 /cancelsession 可随时取消"
                )
                
                self.session_generation_tasks[user_id] = {
                    'step': 'api_id',
                    'data': {}
                }
            
        except Exception as e:
            await event.reply(f"❌ 启动生成失败: {str(e)}")
    
    async def _cancel_session(self, event):
        """取消 SESSION 生成"""
        try:
            user_id = event.sender_id
            
            if user_id not in self.session_generation_tasks:
                await event.reply("❌ 您没有正在进行的 SESSION 生成任务")
                return
            
            del self.session_generation_tasks[user_id]
            await event.reply("✅ SESSION 生成任务已取消")
            
        except Exception as e:
            await event.reply(f"❌ 取消失败: {str(e)}")
    
    async def _handle_session_generation_input(self, event):
        """处理 SESSION 生成过程中的用户输入"""
        user_id = event.sender_id
        
        if user_id not in self.session_generation_tasks:
            return
        
        task = self.session_generation_tasks[user_id]
        step = task['step']
        data = task['data']
        text = event.text.strip()
        
        try:
            if step == 'api_id':
                try:
                    api_id = int(text)
                    data['api_id'] = api_id
                    task['step'] = 'api_hash'
                    await event.reply(
                        "✅ API_ID 已接收\n\n"
                        "2️⃣ 请发送您的 **API_HASH**\n"
                        "   (从 my.telegram.org 获取)"
                    )
                except ValueError:
                    await event.reply("❌ API_ID 必须是数字，请重新发送")
                    
            elif step == 'api_hash':
                if len(text) < 10:
                    await event.reply("❌ API_HASH 格式无效，请重新发送")
                    return
                
                data['api_hash'] = text
                task['step'] = 'phone'
                await event.reply(
                    "✅ API_HASH 已接收\n\n"
                    "3️⃣ 请发送您的 **手机号码**\n"
                    "   (包含国家代码，例如：+8613800138000)"
                )
                
            elif step == 'phone':
                if not text.startswith('+'):
                    await event.reply("❌ 手机号码必须包含国家代码(以 + 开头)，请重新发送")
                    return
                
                data['phone'] = text
                
                await event.reply("⏳ 正在发送验证码，请稍候...")
                
                temp_client = Client(
                    f"temp_session_{user_id}",
                    api_id=data['api_id'],
                    api_hash=data['api_hash'],
                    phone_number=data['phone'],
                    in_memory=True
                )
                
                try:
                    await temp_client.connect()
                    sent_code = await temp_client.send_code(data['phone'])
                    data['phone_code_hash'] = sent_code.phone_code_hash
                    data['client'] = temp_client
                    # 使用time.time()替代asyncio.get_event_loop().time()以确保一致性
                    data['code_sent_time'] = time.time()
                    task['step'] = 'code'
                    
                    await event.reply(
                        "✅ 验证码已发送到您的 Telegram 账号\n\n"
                        "4️⃣ 请发送收到的 **验证码**\n"
                        "   (5位数字)\n\n"
                        "⚠️ 验证码有效期3分钟，请尽快输入"
                    )
                except Exception as e:
                    await temp_client.disconnect()
                    await event.reply(f"❌ 发送验证码失败: {str(e)}\n\n请使用 /generatesession 重新开始")
                    del self.session_generation_tasks[user_id]
                    
            elif step == 'code':
                code = text.replace('-', '').replace(' ', '')
                
                if not code.isdigit() or len(code) != 5:
                    await event.reply("❌ 验证码格式无效(应为5位数字)，请重新发送")
                    return
                
                temp_client = data.get('client')
                if not temp_client:
                    await event.reply("❌ 会话已过期，请使用 /generatesession 重新开始")
                    del self.session_generation_tasks[user_id]
                    return
                
                phone_code_hash = data.get('phone_code_hash')
                if not phone_code_hash:
                    await event.reply("❌ 未找到验证码哈希值，请使用 /generatesession 重新开始")
                    del self.session_generation_tasks[user_id]
                    return
                
                try:
                    await event.reply("⏳ 正在验证验证码...")
                    await temp_client.sign_in(data['phone'], phone_code_hash, code)
                except Exception as sign_in_error:
                    # 检查是否需要密码
                    if "password" in str(sign_in_error).lower() or "two_factor" in str(sign_in_error).lower():
                        task['step'] = 'password'
                        await event.reply(
                            "🔐 检测到您的账户启用了两步验证\n\n"
                            "请发送您的 **两步验证密码**"
                        )
                        return
                    else:
                        await event.reply(f"❌ 验证码验证失败: {str(sign_in_error)}\n\n请使用 /generatesession 重新开始")
                        await temp_client.disconnect()
                        del self.session_generation_tasks[user_id]
                        return
                
                # 登录成功，生成SESSION
                session_string = await temp_client.export_session_string()
                
                await temp_client.disconnect()
                
                del self.session_generation_tasks[user_id]
                
                success = await session_service.save_session(user_id, session_string)
                
                if success:
                    await event.reply(
                        "✅ **SESSION 生成成功！**\n\n"
                        "SESSION 已自动保存到数据库\n"
                        "重启机器人后即可使用\n\n"
                        "🔐 使用 /mysession 查看您的 SESSION"
                    )
                else:
                    await event.reply(
                        f"✅ **SESSION 生成成功！**\n\n"
                        f"您的 SESSION 字符串：\n\n"
                        f"`{session_string}`\n\n"
                        f"⚠️ 但自动保存失败，请手动保存到 .env 文件"
                    )
            
            elif step == 'password':
                # 处理两步验证密码
                temp_client = data.get('client')
                if not temp_client:
                    await event.reply("❌ 会话已过期，请使用 /generatesession 重新开始")
                    del self.session_generation_tasks[user_id]
                    return
                
                password = text.strip()
                if not password:
                    await event.reply("❌ 密码不能为空，请重新发送")
                    return
                
                try:
                    await event.reply("⏳ 正在验证两步验证密码...")
                    await temp_client.check_password(password)
                except Exception as pwd_error:
                    await event.reply(f"❌ 两步验证密码错误: {str(pwd_error)}\n\n请重新发送密码")
                    return
                
                # 密码验证成功，继续生成SESSION
                session_string = await temp_client.export_session_string()
                
                await temp_client.disconnect()
                
                del self.session_generation_tasks[user_id]
                
                success = await session_service.save_session(user_id, session_string)
                
                if success:
                    await event.reply(
                        "✅ **SESSION 生成成功！**\n\n"
                        "SESSION 已自动保存到数据库\n"
                        "重启机器人后即可使用\n\n"
                        "🔐 使用 /mysession 查看您的 SESSION"
                    )
                else:
                    await event.reply(
                        f"✅ **SESSION 生成成功！**\n\n"
                        f"您的 SESSION 字符串：\n\n"
                        f"`{session_string}`\n\n"
                        f"⚠️ 但自动保存失败，请手动保存到 .env 文件"
                    )
                    
        except Exception as e:
            await event.reply(f"❌ 处理失败: {str(e)}\n\n请使用 /generatesession 重新开始")
            if user_id in self.session_generation_tasks:
                del self.session_generation_tasks[user_id]
    
    async def _handle_text_input(self, event):
        """处理文本输入,用于 SESSION 生成流程"""
        user_id = event.sender_id
        
        if user_id in self.session_generation_tasks:
            await self._handle_session_generation_input(event)

# 创建插件实例并注册
session_plugin = SessionPlugin()

# 注册到插件注册表
from ..core.base_plugin import plugin_registry
plugin_registry.register(session_plugin)
