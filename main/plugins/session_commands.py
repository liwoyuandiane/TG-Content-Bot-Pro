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
        
        # 更彻底的清理字符串，移除所有非base64字符
        cleaned_session = re.sub(r'[^A-Za-z0-9+/=]', '', session_string)
        
        # 基本长度检查
        if len(cleaned_session) < 50:
            return False, "SESSION字符串长度不足"
        
        # 对于可能被截断的字符串，我们采用更宽松的验证
        # 只要清理后的字符串看起来像Base64格式即可
        if re.match(r'^[A-Za-z0-9+/]*={0,2}$', cleaned_session):
            return True, "有效"
        
        return False, "SESSION字符串格式无效"
    
    async def _add_session(self, event):
        """添加 SESSION 字符串"""
        try:
            text = event.text.strip()
            
            # 检查是否是直接跟在命令后面的 SESSION 字符串
            if len(text.split(maxsplit=1)) >= 2:
                session_string = text.split(maxsplit=1)[1].strip()
            else:
                # 如果没有直接提供，启动一个对话来获取 SESSION 字符串
                async with self.clients.bot.conversation(event.chat_id) as conv:
                    await conv.send_message(
                        "**请输入 SESSION 字符串**\n\n"
                        "请直接发送您的 SESSION 字符串，我会自动处理其中可能包含的换行符和空格。\n\n"
                        "提示：您可以从 @sessionbot 或通过运行 get_session.py 脚本获取 SESSION 字符串。"
                    )
                    try:
                        response = await conv.get_response(timeout=120)
                        session_string = response.text.strip()
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
            
            # 使用清理后的 SESSION 字符串
            import re
            cleaned_session = re.sub(r'[^A-Za-z0-9+/=]', '', session_string)
            
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
                # 尝试动态刷新 userbot SESSION
                try:
                    from ..core.clients import client_manager
                    refresh_success = await client_manager.refresh_userbot_session(cleaned_session)
                    if refresh_success:
                        await event.reply(
                            "✅ SESSION 已保存并生效\n\n"
                            "Userbot 客户端已自动更新，无需重启机器人\n"
                            "使用 /sessions 查看所有会话"
                        )
                    else:
                        await event.reply(
                            "✅ SESSION 已保存到 MongoDB\n\n"
                            "重启机器人后生效\n"
                            "使用 /sessions 查看所有会话"
                        )
                except Exception as refresh_error:
                    self.logger.error(f"动态刷新 SESSION 失败: {refresh_error}")
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
                msg += f"   SESSION: {session_preview}\n\n"
            
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
                    "使用 /addsession 添加"
                )
                return
            
            msg = "🔐 **您的 SESSION 信息**\n\n"
            msg += f"用户ID: {event.sender_id}\n"
            msg += f"SESSION: {session}\n\n"
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
                phone_number = data['phone']
                
                await event.reply("⏳ 正在发送验证码，请稍候...")
                
                temp_client = Client(
                    f"temp_session_{user_id}",
                    api_id=data['api_id'],
                    api_hash=data['api_hash'],
                    device_model="TG-Content-Bot Session Generator",
                    in_memory=True
                )
                
                try:
                    await temp_client.connect()
                    self.logger.info(f"客户端已连接，准备发送验证码到: {phone_number}")
                    
                    sent_code = await temp_client.send_code(phone_number)
                    
                    # 详细日志
                    self.logger.info(f"send_code 返回: type={sent_code.type}, hash={sent_code.phone_code_hash[:20]}..., timeout={sent_code.timeout}")
                    
                    data['phone_code_hash'] = sent_code.phone_code_hash
                    data['client'] = temp_client
                    data['code_sent_time'] = time.time()
                    data['sent_code_type'] = str(sent_code.type)
                    task['step'] = 'code'
                    
                    # 根据验证码类型提供明确指引
                    code_type_str = str(sent_code.type)
                    if "APP" in code_type_str.upper():
                        instruction = (
                            "✅ **验证码已通过 Telegram 应用内消息发送**\n\n"
                            "📱 **验证码查找方法**:\n"
                            "1️⃣ 查看 Telegram 通知栏\n"
                            "2️⃣ 在聊天列表顶部查找 \"Telegram\" 官方账号\n"
                            "3️⃣ 检查是否有验证码弹窗\n\n"
                            "❓ **看不到验证码？**\n"
                            "• 发送 `resend` 切换为短信接收\n"
                            "• 或直接发送验证码: `1 2 3 4 5`\n\n"
                            f"⏱ 下一种方式: {sent_code.next_type if sent_code.next_type else '短信'}"
                        )
                    elif "SMS" in code_type_str.upper():
                        instruction = (
                            "✅ **验证码已通过短信发送到您的手机**\n\n"
                            "📱 请查看手机短信，然后发送验证码\n"
                            "格式: `1 2 3 4 5` (用空格分隔)"
                        )
                    else:
                        instruction = (
                            f"✅ 验证码已发送（类型: {sent_code.type}）\n\n"
                            "请输入收到的验证码，格式: `1 2 3 4 5`"
                        )
                    
                    await event.reply(instruction)
                except Exception as e:
                    self.logger.error(f"发送验证码失败: {type(e).__name__}: {str(e)}")
                    await temp_client.disconnect()
                    # 提供更友好的错误提示信息
                    error_msg = "❌ 发送验证码失败\n\n"
                    if "FLOOD_WAIT" in str(e).upper():
                        # 解析 FloodWait 错误中的等待时间
                        import re
                        flood_match = re.search(r'(\d+)', str(e))
                        if flood_match:
                            wait_seconds = int(flood_match.group(1))
                            hours = wait_seconds // 3600
                            minutes = (wait_seconds % 3600) // 60
                            if hours > 0:
                                error_msg += f"由于 Telegram 限制，需要等待 {hours} 小时 {minutes} 分钟后才能重试。\n\n"
                            else:
                                error_msg += f"由于 Telegram 限制，需要等待 {minutes} 分钟后才能重试。\n\n"
                        else:
                            error_msg += "由于 Telegram 限制，需要等待一段时间后才能重试。\n\n"
                    else:
                        error_msg += f"错误信息: {str(e)}\n\n"
                    
                    error_msg += "可能的原因:\n"
                    error_msg += "• 手机号码已被 Telegram 临时限制\n"
                    error_msg += "• API_ID 或 API_HASH 不正确\n"
                    error_msg += "• 服务器 IP 被 Telegram 限制\n\n"
                    error_msg += "解决方案:\n"
                    error_msg += "• 等待限制时间解除后重试\n"
                    error_msg += "• 检查 API 凭证是否正确\n"
                    error_msg += "• 尝试使用本地脚本生成 SESSION:\n"
                    error_msg += "  python3 get_session.py\n"
                    error_msg += "• 更换手机号码或服务器 IP\n\n"
                    error_msg += "使用 /generatesession 重新开始"
                    
                    await event.reply(error_msg)
                    del self.session_generation_tasks[user_id]
                    
            elif step == 'code':
                # 检查是否是重新发送请求
                if text.lower() == 'resend':
                    temp_client = data.get('client')
                    if not temp_client:
                        await event.reply("❌ 会话已过期，请使用 /generatesession 重新开始")
                        del self.session_generation_tasks[user_id]
                        return
                    
                    try:
                        await event.reply("⏳ 正在重新发送验证码...")
                        phone_code_hash = data.get('phone_code_hash')
                        phone_number = data.get('phone')
                        sent_code = await temp_client.resend_code(phone_number, phone_code_hash)
                        
                        # 更新验证码类型信息
                        data['sent_code_type'] = str(sent_code.type)
                        
                        # 根据新验证码类型提供指引
                        code_type_str = str(sent_code.type)
                        if "APP" in code_type_str.upper():
                            instruction = (
                                "✅ **验证码已重新通过 Telegram 应用内消息发送**\n\n"
                                "📱 **验证码查找方法**:\n"
                                "1️⃣ 查看 Telegram 通知栏\n"
                                "2️⃣ 在聊天列表顶部查找 \"Telegram\" 官方账号\n"
                                "3️⃣ 检查是否有验证码弹窗\n\n"
                                "请发送收到的验证码，格式: `1 2 3 4 5`"
                            )
                        elif "SMS" in code_type_str.upper():
                            instruction = (
                                "✅ **验证码已重新通过短信发送到您的手机**\n\n"
                                "📱 请查看手机短信，然后发送验证码\n"
                                "格式: `1 2 3 4 5` (用空格分隔)"
                            )
                        else:
                            instruction = (
                                f"✅ 验证码已重新发送（类型: {sent_code.type}）\n\n"
                                "请输入收到的验证码，格式: `1 2 3 4 5`"
                            )
                        
                        await event.reply(instruction)
                        return
                    except Exception as resend_error:
                        await event.reply(f"❌ 重新发送验证码失败: {str(resend_error)}\n\n请使用 /generatesession 重新开始")
                        await temp_client.disconnect()
                        del self.session_generation_tasks[user_id]
                        return
                
                code = text.replace('-', '').replace(' ', '')
                
                if not code.isdigit() or len(code) != 5:
                    await event.reply("❌ 验证码格式无效(应为5位数字)，请重新发送")
                    return
                
                temp_client = data.get('client')
                if not temp_client:
                    await event.reply("❌ 会话已过期，请使用 /generatesession 重新开始")
                    del self.session_generation_tasks[user_id]
                    return
                
                code_sent_time = data.get('code_sent_time', 0)
                # 修复时间判断逻辑，确保code_sent_time有效且未超时
                if code_sent_time > 0:
                    # 使用time.time()确保时间计算一致性
                    elapsed_time = time.time() - code_sent_time
                    if elapsed_time > self.CODE_TIMEOUT:
                        if temp_client:
                            await temp_client.disconnect()
                        await event.reply(
                            "❌ 验证码已过期(超过3分钟)\n\n"
                            "请使用 /generatesession 重新开始"
                        )
                        del self.session_generation_tasks[user_id]
                        return
                
                # 使用验证码登录
                try:
                    await event.reply("⏳ 正在验证验证码...")
                    phone_code_hash = data.get('phone_code_hash')
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