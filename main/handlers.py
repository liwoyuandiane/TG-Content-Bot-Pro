"""Pyrogram 消息处理器"""
import logging
import re
from pyrogram import Client, filters

from .core.clients import client_manager
from .core.database import db_manager
from .services.message_service import forward_message, parse_link
from .services.user_service import user_service
from .services.session_service import session_service
from .services.permission_service import permission_service
from .utils.session_utils import validate_pyrogram_session
from .config import settings

logger = logging.getLogger(__name__)

# 用户状态管理
user_states = {}  # user_id -> {"state": "waiting_phone", "phone": None}

def register_all_handlers(bot: Client):
    """注册所有消息处理器"""

    @bot.on_message(filters.command("start"))
    async def start_command(client, message):
        user_id = message.from_user.id

        if not await user_service.is_user_authorized(user_id):
            await message.reply("❌ 您没有权限使用此机器人")
            return

        user = message.from_user
        is_auth = await user_service.is_user_authorized(user_id)
        await user_service.add_user(
            user_id=user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            is_authorized=is_auth
        )

        if await user_service.is_user_banned(user_id):
            await message.reply("您已被封禁，无法使用此机器人。")
            return

        stats = await user_service.get_user_stats(user_id)

        text = "发送任意消息链接即可转发到这里。对于私密频道消息，请先发送邀请链接。\n\n"
        if stats:
            text += "📊 您的统计:\n"
            text += f"• 总转发: {stats['total_forwards']}\n"
            text += f"• 总大小: {stats['total_size'] / (1024*1024):.2f} MB\n\n"
        text += "**支持:** @tgxxtq"

        await message.reply(text)

    @bot.on_message(filters.command("help"))
    async def help_command(client, message):
        await message.reply(
            "📖 **帮助**\n\n"
            "• 发送消息链接转发内容\n"
            "• /start - 开始使用\n"
            "• /help - 显示帮助\n"
            "• /plan - 账户信息\n"
            "• /batch - 批量保存\n"
            "• /cancel - 取消任务\n"
            "• /generatesession - 生成 SESSION\n"
            "• /mysession - 查看 SESSION\n"
            "• /history - 转发历史\n"
            "• /clearhistory - 清除历史\n"
            "• /sessions - 所有SESSION (仅管理员)"
        )

    @bot.on_message(filters.command("plan"))
    async def plan_command(client, message):
        user_id = message.from_user.id

        if not await permission_service.require_authorized(user_id):
            return

        user = await user_service.get_user(user_id)
        if not user:
            await message.reply("❌ 用户不存在，请发送 /start")
            return

        plan_name = user.get("plan", "free")
        expires = user.get("plan_expires", "无")

        text = "👑 **账户信息**\n\n"
        text += f"• 用户ID: `{user_id}`\n"
        text += f"• 当前套餐: **{plan_name}**\n"
        if expires != "无":
            text += f"• 过期时间: {expires}\n"
        text += "\n发送消息链接开始转发"

        await message.reply(text)

    @bot.on_message(filters.command("batch"))
    async def batch_command(client, message):
        user_id = message.from_user.id

        if not await permission_service.require_authorized(user_id):
            return

        await message.reply(
            "📦 **批量保存模式**\n\n"
            "请发送起始消息链接，我会问您需要向下转发几条"
        )
        user_states[user_id] = {"state": "batch_waiting_link", "link": None, "count": None}

    @bot.on_message(filters.command("cancel"))
    async def cancel_command(client, message):
        user_id = message.from_user.id

        if user_id in user_states:
            user_states.pop(user_id, None)
            await message.reply("✅ 已取消当前任务")
        else:
            await message.reply("❌ 没有正在进行的任务")

    @bot.on_message(filters.command("history"))
    async def history_command(client, message):
        user_id = message.from_user.id

        if not await permission_service.require_authorized(user_id):
            return

        history = await db_manager.get_forward_history(user_id, limit=10)
        if not history:
            await message.reply("暂无转发历史")
            return

        msg = "📜 **转发历史**\n\n"
        for item in history:
            link = item.get('message_link', item.get('msg_link', 'N/A'))
            is_batch = item.get('batch', False)
            batch_count = item.get('batch_count')
            if is_batch and batch_count:
                msg += f"• 📦 批量转发 `{link}`（{batch_count} 条消息）\n"
            else:
                msg += f"• {link}\n"
            msg += f"  状态: {item.get('status', 'unknown')}\n\n"

        await message.reply(msg)

    @bot.on_message(filters.command("clearhistory"))
    async def clear_history_command(client, message):
        user_id = message.from_user.id

        if not await permission_service.require_owner(user_id):
            await message.reply("❌ 仅管理员可用")
            return

        await db_manager.clear_forward_history(user_id)
        await message.reply("✅ 历史已清除")

    @bot.on_message(filters.command("sessions"))
    async def list_sessions_command(client, message):
        user_id = message.from_user.id

        if not await permission_service.require_owner(user_id):
            await message.reply("❌ 仅管理员可用")
            return

        sessions = await session_service.get_all_sessions()
        if not sessions:
            await message.reply("📭 暂无 SESSION")
            return

        msg = "📋 **SESSION 列表**\n\n"
        for i, s in enumerate(sessions, 1):
            msg += f"{i}. 用户: {s.get('user_id')}\n"

        await message.reply(msg)

    @bot.on_message(filters.command("addsession"))
    async def add_session_command(client, message):
        user_id = message.from_user.id

        # 涉及全局 userbot SESSION, 仅管理员可用
        if not await permission_service.require_owner(user_id):
            await message.reply("❌ 仅管理员可用")
            return

        text = message.text.strip()
        if len(text.split(maxsplit=1)) >= 2:
            session_string = text.split(maxsplit=1)[1].strip()
            if validate_pyrogram_session(session_string):
                await session_service.save_session(user_id, session_string)

                # 自动启动 userbot
                settings.SESSION = session_string
                await client_manager.refresh_userbot_session(session_string)

                await message.reply("✅ SESSION 已保存，Userbot 已启动")
            else:
                await message.reply("❌ SESSION 格式无效")
        else:
            await message.reply("用法: /addsession <session_string>\n\n示例: /addsession BgA...")

    @bot.on_message(filters.command("delsession"))
    async def del_session_command(client, message):
        user_id = message.from_user.id

        if not await permission_service.require_owner(user_id):
            await message.reply("❌ 仅管理员可用")
            return

        text = message.text.strip()
        parts = text.split()

        target = user_id
        if len(parts) >= 2:
            if parts[1].lower() == "me":
                target = user_id
            else:
                try:
                    target = int(parts[1])
                except:
                    await message.reply("❌ 参数无效")
                    return

        success = await session_service.delete_session(target)
        await message.reply("✅ 已删除" if success else "❌ 删除失败")

    @bot.on_message(filters.command("authorize"))
    async def authorize_command(client, message):
        user_id = message.from_user.id

        if not await permission_service.require_owner(user_id):
            await message.reply("❌ 仅管理员可用")
            return

        parts = message.text.split()
        if len(parts) < 2:
            await message.reply("用法: /authorize 123456789")
            return

        try:
            target_id = int(parts[1])
            success = await user_service.authorize_user(target_id)
            await message.reply(f"✅ 已授权用户 {target_id}" if success else "❌ 授权失败")
        except ValueError:
            await message.reply("❌ 无效的用户 ID")

    @bot.on_message(filters.command("unauthorize"))
    async def unauthorize_command(client, message):
        user_id = message.from_user.id

        if not await permission_service.require_owner(user_id):
            await message.reply("❌ 仅管理员可用")
            return

        parts = message.text.split()
        if len(parts) < 2:
            await message.reply("用法: /unauthorize 123456789")
            return

        try:
            target_id = int(parts[1])
            success = await user_service.unauthorize_user(target_id)
            await message.reply(f"✅ 已取消授权用户 {target_id}" if success else "❌ 取消授权失败")
        except ValueError:
            await message.reply("❌ 无效的用户 ID")

    @bot.on_message(filters.command("authorized"))
    async def authorized_command(client, message):
        user_id = message.from_user.id

        if not await permission_service.require_owner(user_id):
            await message.reply("❌ 仅管理员可用")
            return

        users = await user_service.get_authorized_users()
        if not users:
            await message.reply("📭 暂无授权用户")
            return

        msg = "📋 **授权用户列表**\n\n"
        for i, uid in enumerate(users, 1):
            msg += f"{i}. `{uid}`\n"

        await message.reply(msg)

    @bot.on_message(filters.command("upgrade"))
    async def upgrade_command(client, message):
        user_id = message.from_user.id

        if not await permission_service.require_owner(user_id):
            await message.reply("❌ 仅管理员可用")
            return

        parts = message.text.split()
        if len(parts) < 2:
            await message.reply("用法: /upgrade 123456789")
            return

        try:
            target_id = int(parts[1])
            success = await user_service.set_user_premium(target_id, True)
            await message.reply(f"✅ 已升级用户 {target_id} 为 Premium" if success else "❌ 升级失败")
        except ValueError:
            await message.reply("❌ 无效的用户 ID")

    @bot.on_message(filters.command("downgrade"))
    async def downgrade_command(client, message):
        user_id = message.from_user.id

        if not await permission_service.require_owner(user_id):
            await message.reply("❌ 仅管理员可用")
            return

        parts = message.text.split()
        if len(parts) < 2:
            await message.reply("用法: /downgrade 123456789")
            return

        try:
            target_id = int(parts[1])
            success = await user_service.set_user_premium(target_id, False)
            await message.reply(f"✅ 已降级用户 {target_id} 为普通用户" if success else "❌ 降级失败")
        except ValueError:
            await message.reply("❌ 无效的用户 ID")

    @bot.on_message(filters.command("queue"))
    async def queue_command(client, message):
        user_id = message.from_user.id

        if not await permission_service.require_owner(user_id):
            await message.reply("❌ 仅管理员可用")
            return

        await message.reply("📋 队列功能\n\n队列状态: 正常")

    @bot.on_message(filters.command("generatesession"))
    async def generate_session(client, message):
        user_id = message.from_user.id

        if not await permission_service.require_authorized(user_id):
            await message.reply("❌ 您没有权限")
            return

        if not settings.API_ID or not settings.API_HASH:
            await message.reply("❌ 未配置 API 凭证")
            return

        user_states[user_id] = {"state": "waiting_phone", "phone": None}
        await message.reply("📱 请发送您的手机号码（如 +8613800138000）")

    def parse_phone_number(text: str) -> str:
        """解析并标准化手机号格式"""
        # 移除所有空格、括号、横杠（支持 +1(682) 800-4917 或 +1 682 800 4917 等格式）
        cleaned = re.sub(r'[\s\(\)\-\+]', '', text)

        # 如果以 00 开头，替换为 +
        if cleaned.startswith('00'):
            cleaned = cleaned[2:]

        # 确保是数字
        if not cleaned.isdigit():
            return None

        # 添加 + 前缀
        return '+' + cleaned

    @bot.on_message(filters.command("retry_session"))
    async def retry_session(client, message):
        user_id = message.from_user.id
        session = await session_service.get_session(user_id)

        if not session:
            await message.reply("❌ 未找到 SESSION")
            return

        settings.SESSION = session
        success = await client_manager.refresh_userbot_session(session)

        await message.reply("✅ Userbot 已启动" if success else "❌ 启动失败")

    @bot.on_message(filters.command("mysession"))
    async def my_session(client, message):
        from .utils.session_utils import get_session_info

        user_id = message.from_user.id
        if not await permission_service.require_authorized(user_id):
            return

        session = await session_service.get_session(user_id)
        if not session:
            await message.reply("❌ 暂无 SESSION")
            return

        info = get_session_info(session)
        msg = f"🔐 **SESSION**\n\n有效性: {'✅' if info.get('valid') else '❌'}\n长度: {len(session)} 字符\n\n||`{session}`||"
        await message.reply(msg)

    @bot.on_message(filters.text)
    async def handle_message(client, message):
        """处理文本消息，转发 Telegram 链接"""
        # 跳过命令消息
        if message.text and message.text.startswith('/'):
            return

        # 兼容匿名管理员/频道身份消息(from_user 可能为 None)
        if not message.from_user:
            logger.warning(f"收到无发送者消息, 忽略: {getattr(message, 'text', '')[:50]}")
            return

        user_id = message.from_user.id
        text = message.text.strip()

        # ===== 批量保存流程 =====
        # 阶段1: 等待用户发送起始链接
        if user_id in user_states and user_states[user_id].get("state") == "batch_waiting_link":
            # 提取链接
            import re as _re
            links = _re.findall(r'https?://(?:t\.me|telegram\.me)/[^\s，。；]+', text)
            if not links:
                await message.reply("❌ 未找到有效的链接，请重新发送起始链接（或 /cancel 退出）")
                return

            # 保存链接, 询问条数
            user_states[user_id] = {"state": "batch_waiting_count", "link": links[0], "count": None}
            await message.reply(
                f"✅ 已记录起始链接：\n`{links[0]}`\n\n"
                "📥 请发送要转发的条数（包含此条，向下 N 条，如 5 表示本条+后4条）\n"
                "发送 /cancel 可取消"
            )
            return

        # 阶段2: 等待用户输入条数
        if user_id in user_states and user_states[user_id].get("state") == "batch_waiting_count":
            state = user_states[user_id]
            link = state.get("link")

            # 解析数字
            count_text = text.strip()
            if not count_text.isdigit():
                await message.reply("❌ 请输入数字条数，如：5（或 /cancel 退出）")
                return

            count = int(count_text)
            if count <= 0 or count > 30:
                await message.reply("❌ 条数必须在 1-30 之间")
                return

            user_states.pop(user_id, None)  # 先清除状态, 防止失败重入

            if not link:
                await message.reply("❌ 未找到起始链接，请重新 /batch")
                return

            # 权限检查
            if not await user_service.is_user_authorized(user_id):
                return

            # 解析起始链接
            chat_id, start_msg_id = parse_link(link)
            if chat_id is None or start_msg_id is None:
                await message.reply("❌ 起始链接格式无效")
                return

            # 逐条转发: msg_id, msg_id+1, ..., msg_id+count-1
            await message.reply(f"📦 开始批量转发 {count} 条...")
            success_count = 0
            fail_links = []
            for i in range(count):
                current_msg_id = start_msg_id + i
                # 构造消息链接(私有频道用 /c/ 格式, 公开用 username/msgid)
                if isinstance(chat_id, int) and chat_id < 0:
                    sub_link = f"https://t.me/c/{str(chat_id)[4:]}/{current_msg_id}"
                else:
                    sub_link = f"https://t.me/{chat_id}/{current_msg_id}"

                try:
                    ok, err = await forward_message(
                        userbot=client_manager.userbot,
                        bot=client_manager.bot,
                        user_id=user_id,
                        msg_link=sub_link
                    )
                    if ok:
                        success_count += 1
                    else:
                        fail_links.append(f"{sub_link} ({err})")
                except Exception as e:
                    logger.error(f"批量转发 {sub_link} 失败: {e}")
                    fail_links.append(f"{sub_link} ({str(e)[:30]})")

            # 记录一条批量转发记录(起始链接 + 条数 + 成功数)
            if success_count > 0:
                try:
                    await db_manager.add_forward(
                        user_id=user_id,
                        message_link=link,
                        message_id=start_msg_id,
                        chat_id=str(chat_id),
                        media_type="media",
                        file_size=0,
                        status="success",
                        message_meta={
                            "batch": True,
                            "batch_count": success_count,
                            "batch_requested": count,
                            "batch_start": start_msg_id
                        }
                    )
                except Exception as se:
                    logger.warning(f"批量记录统计失败: {se}")
                # 统计按真实转发条数累加(批量记录本身 +1, 这里补上剩余的)
                try:
                    if success_count > 1:
                        db_manager.db.users.update_one(
                            {"user_id": user_id},
                            {"$inc": {"total_forwards": success_count - 1}}
                        )
                except Exception as se:
                    logger.warning(f"批量统计补记失败: {se}")

            # 汇总(静默成功, 仅失败提示)
            if fail_links:
                summary = f"⚠️ 批量完成：成功 {success_count} 条，失败 {len(fail_links)} 条\n"
                summary += "\n".join(f"• {f}" for f in fail_links[:5])
                if len(fail_links) > 5:
                    summary += f"\n... 等 {len(fail_links)} 条"
                await message.reply(summary)
            return

        # 处理用户状态（等待输入手机号）
        if user_id in user_states and user_states[user_id].get("state") == "waiting_phone":
            phone = parse_phone_number(text)
            if not phone:
                await message.reply("❌ 手机号格式无效，请重新发送（如 +8613800138000）")
                return

            await message.reply("📱 正在发送验证码...\n请稍候...")

            # 发送验证码
            from .services.session_generator import generate_session_by_phone
            success, result = await generate_session_by_phone(phone)

            if success:
                user_states[user_id] = {"state": "waiting_code", "phone": phone}
                await message.reply(f"✅ 验证码已发送！\n\n{result}")
            else:
                user_states.pop(user_id, None)
                await message.reply(f"❌ 发送失败: {result}")
            return

        # 处理用户状态（等待输入验证码）
        if user_id in user_states and user_states[user_id].get("state") == "waiting_code":
            state = user_states[user_id]
            phone = state.get("phone")
            # 移除所有空格（支持 8 7 3 7 6 格式）
            code = text.strip().replace(" ", "")

            if not phone:
                user_states.pop(user_id, None)
                await message.reply("❌ 会话已过期，请重新发送 /generatesession")
                return

            await message.reply("🔐 正在验证验证码...")

            from .services.session_generator import verify_phone_code
            success, result = await verify_phone_code(phone, code)

            if success:
                await session_service.save_session(user_id, result)
                user_states.pop(user_id, None)

                # 自动启动 userbot
                settings.SESSION = result
                await client_manager.refresh_userbot_session(result)

                await message.reply(
                    "✅ SESSION 生成成功！\n\n"
                    "您的 Userbot 已自动启动，可以转发私密频道消息了"
                )
            elif result == "NEED_PASSWORD":
                # 需要两步验证密码
                user_states[user_id]["state"] = "waiting_password"
                await message.reply("🔑 您的账号启用了两步验证，请发送密码：")
            else:
                user_states.pop(user_id, None)
                await message.reply(f"❌ 验证失败: {result}\n请重新发送 /generatesession 重试")
            return

        # 处理用户状态（等待输入两步验证密码）
        if user_id in user_states and user_states[user_id].get("state") == "waiting_password":
            state = user_states[user_id]
            phone = state.get("phone")
            password = text.strip()

            if not phone:
                user_states.pop(user_id, None)
                await message.reply("❌ 会话已过期，请重新发送 /generatesession")
                return

            await message.reply("🔐 正在验证密码...")

            from .services.session_generator import verify_password
            success, result = await verify_password(phone, password)

            user_states.pop(user_id, None)

            if success:
                await session_service.save_session(user_id, result)

                # 自动启动 userbot
                settings.SESSION = result
                await client_manager.refresh_userbot_session(result)

                await message.reply(
                    "✅ SESSION 生成成功！\n\n"
                    "您的 Userbot 已自动启动，可以转发私密频道消息了"
                )
            else:
                await message.reply(f"❌ 密码错误: {result}\n请重新发送 /generatesession 重试")
            return

        # 权限检查
        if not await user_service.is_user_authorized(user_id):
            return

        # 检查链接
        if not any(domain in text.lower() for domain in ['t.me/', 'telegram.me/']):
            return

        # 提取链接(支持一条消息多个链接, 每行一个)
        import re as _re
        links = _re.findall(r'https?://(?:t\.me|telegram\.me)/[^\s，。；]+', text)
        if not links:
            await message.reply("❌ 未找到有效的链接")
            return

        # 逐条转发
        success_count = 0
        fail_messages = []
        for link in links:
            try:
                success, result_msg = await forward_message(
                    userbot=client_manager.userbot,
                    bot=client_manager.bot,
                    user_id=user_id,
                    msg_link=link
                )
                if success:
                    success_count += 1
                    # 更新转发统计(消息历史 + 用户计数)
                    try:
                        chat_id, msg_id = parse_link(link)
                        await db_manager.add_forward(
                            user_id=user_id,
                            message_link=link,
                            message_id=msg_id or 0,
                            chat_id=str(chat_id or ""),
                            media_type="media",
                            file_size=0,
                            status="success"
                        )
                    except Exception as stat_err:
                        logger.warning(f"记录转发统计失败: {stat_err}")
                else:
                    fail_messages.append(f"{link}: {result_msg}")
            except Exception as e:
                logger.error(f"处理链接失败 {link}: {e}", exc_info=True)
                fail_messages.append(f"{link}: {str(e)[:30]}")

        # 汇总提示: 成功静默(内容已送达), 仅失败需要提示
        try:
            if fail_messages:
                summary = "❌ 部分失败:\n" + "\n".join(f"• {m}" for m in fail_messages[:5])
                if len(fail_messages) > 5:
                    summary += f"\n... 等 {len(fail_messages)} 条"
                await message.reply(summary)
            if not success_count:
                await message.reply("❌ 转发失败")
        except Exception as e:
            logger.warning(f"发送汇总提示失败: {e}")

    @bot.on_callback_query()
    async def handle_callback(client, callback_query):
        """处理回调查询"""
        data = callback_query.data
        user_id = callback_query.from_user.id

        await callback_query.answer()

        if data == "set":
            await callback_query.message.edit("请发送图片作为缩略图...")
        elif data == "rem":
            from .utils.file_manager import file_manager
            user_thumb = f'{user_id}.jpg'
            if file_manager.safe_remove(user_thumb):
                await callback_query.message.edit("✅ 已删除")
            else:
                await callback_query.message.edit("未找到缩略图")