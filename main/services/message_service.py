"""消息服务 - 智能获取与秒级转发方案

核心策略(秒级转发, 不下载重传):
1. bot 直接获取并发送(公开频道: 最快)
2. userbot 获取后 bot 用 file_id 发送
3. 收藏夹中转: userbot 将消息转发到自己收藏夹("me"),
   Telegram 服务端生成新的 file_id(bot 可用的), bot 从收藏夹
   读取后用 file_id 秒级发送给用户(私有频道/受限内容核心方案)
4. userbot 直接转发/发送给用户(兜底)

所有路径都是服务端操作, 无本地下载/重传, 秒级完成。
"""
import logging
import re

from pyrogram import Client
from pyrogram.errors import RPCError

logger = logging.getLogger(__name__)


def parse_link(msg_link: str):
    """解析 Telegram 消息链接

    支持:
    - 公开频道/群组: https://t.me/username/123  / telegram.me/username/123
    - 私有频道:      https://t.me/c/chatid/123
    - 机器人:        https://t.me/b/chatid/123
    - 参数:          ?single / ?comment=xxx 会被剥离

    Returns:
        (chat_id, msg_id) - chat_id 为 int 或 str(username)
        解析失败返回 (None, None)
    """
    if not msg_link:
        return None, None

    msg_link = msg_link.strip()

    # 剥离查询参数 (?single, ?comment=xxx 等)
    if '?' in msg_link:
        msg_link = msg_link.split('?')[0]

    # 匹配 t.me/ 或 telegram.me/
    m = re.search(r'(?:t\.me|telegram\.me)/(.+)', msg_link, re.IGNORECASE)
    if not m:
        return None, None

    path = m.group(1).strip('/')
    parts = path.split('/')

    # 私有频道 /c/chatid/msgid 或 机器人 /b/chatid/msgid
    if parts and parts[0] in ('c', 'b') and len(parts) >= 3:
        try:
            chat_id = int('-100' + parts[1])
            return chat_id, int(parts[2])
        except ValueError:
            return None, None

    # 公开频道/群组 username/msgid
    if len(parts) >= 2 and parts[1].isdigit():
        return parts[0], int(parts[1])

    return None, None


def _is_sendable(msg) -> bool:
    """判断消息是否包含可转发的内容"""
    if msg is None or getattr(msg, 'empty', False):
        return False
    return bool(
        msg.video or msg.video_note or msg.photo or msg.document
        or msg.audio or msg.voice or msg.sticker or msg.animation
        or msg.text or msg.caption or msg.media
    )


async def _send_message_by_type(client: Client, user_id: int, msg) -> bool:
    """按消息类型用 file_id 秒级发送(核心发送函数)

    client: 发送方(bot 或 userbot)
    """
    caption = msg.caption or ""

    try:
        if msg.video:
            m = msg.video
            await client.send_video(
                user_id, m.file_id, caption=caption,
                duration=m.duration, width=m.width, height=m.height,
            )
        elif msg.video_note:
            m = msg.video_note
            await client.send_video_note(
                user_id, m.file_id,
                duration=m.duration, length=m.length,
            )
        elif msg.photo:
            await client.send_photo(user_id, msg.photo.file_id, caption=caption)
        elif msg.audio:
            m = msg.audio
            await client.send_audio(
                user_id, m.file_id, caption=caption,
                duration=m.duration, performer=m.performer, title=m.title,
            )
        elif msg.voice:
            await client.send_voice(user_id, msg.voice.file_id, caption=caption)
        elif msg.sticker:
            await client.send_sticker(user_id, msg.sticker.file_id)
        elif msg.animation:
            m = msg.animation
            await client.send_animation(
                user_id, m.file_id, caption=caption,
                duration=m.duration, width=m.width, height=m.height,
            )
        elif msg.document:
            m = msg.document
            await client.send_document(
                user_id, m.file_id, caption=caption, file_name=m.file_name,
            )
        elif msg.text:
            await client.send_message(user_id, msg.text)
        else:
            return False
        return True
    except RPCError as e:
        logger.error(f"_send_message_by_type 失败: {e}")
        return False
    except Exception as e:
        logger.error(f"_send_message_by_type 异常: {e}")
        return False


async def _get_message(client: Client, chat_id, msg_id):
    """尝试从客户端获取消息"""
    try:
        msg = await client.get_messages(chat_id, msg_id)
        if msg and not getattr(msg, 'empty', False) and _is_sendable(msg):
            return msg
        return None
    except Exception as e:
        logger.warning(f"{client.name}.get_messages 失败: {e}")
        return None


async def _forward_via_favorites(userbot: Client, bot: Client, user_id: int,
                                 chat_id, msg_id) -> bool:
    """收藏夹中转: userbot 转发到收藏夹 → Telegram 生成新 file_id → bot 发送

    这是私有频道/受限内容秒级转发的核心方案:
    - userbot 把消息转发到自己的收藏夹("me"), 服务端会生成全新的
      file_id(与用户 session 绑定, 对 bot 同样有效)
    - bot 从收藏夹读取后用 file_id 秒级发送给用户
    - 全程服务端操作, 无需本地下载
    """
    try:
        logger.info("📌 方案3: 收藏夹中转...")
        forwarded = await userbot.forward_messages(
            chat_id="me",
            from_chat_id=chat_id,
            message_ids=msg_id
        )
        if not forwarded:
            logger.warning("转发到收藏夹失败")
            return False

        if isinstance(forwarded, list):
            saved_msg = forwarded[0]
        else:
            saved_msg = forwarded

        saved_msg_id = saved_msg.id
        logger.info(f"已转发到收藏夹: msg_id={saved_msg_id}")

        # 尝试 bot 从收藏夹读取并联用 file_id 发送(秒级)
        try:
            saved_in_bot = await bot.get_messages("me", saved_msg_id)
            if saved_in_bot and not getattr(saved_in_bot, 'empty', False):
                logger.info(
                    f"bot 从收藏夹读取成功: video={bool(saved_in_bot.video)}, "
                    f"photo={bool(saved_in_bot.photo)}"
                )
                ok = await _send_message_by_type(bot, user_id, saved_in_bot)
                if ok:
                    logger.info("通过收藏夹 + bot file_id 秒级发送成功")
                    # 清理收藏
                    try:
                        await userbot.delete_messages("me", saved_msg_id)
                    except Exception:
                        pass
                    return True
        except Exception as e:
            logger.warning(f"bot 从收藏夹读取失败: {e}")

        # 兜底: userbot 直接转发给用户
        try:
            await userbot.forward_messages(
                chat_id=user_id,
                from_chat_id="me",
                message_ids=saved_msg_id
            )
            logger.info("userbot 从收藏夹直接转发给用户成功")
            # 清理收藏
            try:
                await userbot.delete_messages("me", saved_msg_id)
            except Exception:
                pass
            return True
        except Exception as e:
            logger.warning(f"userbot 从收藏夹转发失败: {e}")

        # 清理残留收藏
        try:
            await userbot.delete_messages("me", saved_msg_id)
        except Exception:
            pass
        return False
    except Exception as e:
        logger.error(f"收藏夹中转失败: {e}")
        return False


async def forward_message(userbot: Client, bot: Client, user_id: int, msg_link: str):
    """转发 Telegram 消息给用户(秒级, 不下载重传)

    Args:
        userbot: 用户客户端(访问受限内容)
        bot: 机器人客户端(发送给用户)
        user_id: 目标用户
        msg_link: 消息链接

    Returns:
        (success: bool, result_msg: str)
    """
    try:
        chat_id, msg_id = parse_link(msg_link)

        # 检查是否成功解析
        if chat_id is None or msg_id is None:
            logger.warning(f"链接格式无效: {msg_link}")
            return False, "❌ 链接格式无效，请使用包含消息ID的链接，如：https://t.me/username/123"

        logger.info(f"解析: chat={chat_id}, msg={msg_id}")

        # ========== 方案1: bot 直接获取并联用 file_id 发送(公开频道) ==========
        if bot and bot.is_connected:
            msg = await _get_message(bot, chat_id, msg_id)
            if msg:
                logger.info(f"bot.get_messages 成功: chat={chat_id}")
                ok = await _send_message_by_type(bot, user_id, msg)
                if ok:
                    logger.info("方案1 bot 秒级发送成功 ✅")
                    return True, ""
                logger.warning("方案1 bot 发送失败, 尝试其它方案")

        # ========== 方案2: userbot 获取后 bot 用 file_id 发送 ==========
        if userbot and userbot.is_connected:
            msg = await _get_message(userbot, chat_id, msg_id)
            if msg:
                logger.info(f"userbot.get_messages 成功: chat={chat_id}")
                # 注意: 私有频道的 file_id 与 userbot session 绑定,
                # bot 发送可能报 MEDIA_EMPTY, 失败会自动走方案3
                ok = await _send_message_by_type(bot, user_id, msg)
                if ok:
                    logger.info("方案2 userbot 获取 + bot 发送成功 ✅")
                    return True, ""
                logger.info("方案2 失败(MEDIA_EMPTY 等), 进入收藏夹中转")

        # ========== 方案3: 收藏夹中转(私有频道/受限内容核心方案) ==========
        if userbot and userbot.is_connected:
            ok = await _forward_via_favorites(userbot, bot, user_id, chat_id, msg_id)
            if ok:
                return True, ""
            return False, "❌ 该消息无法转发（可能是受限内容或已删除）"

        return False, "❌ 无法访问该频道，请配置 SESSION"

    except Exception as e:
        logger.error(f"forward_message 异常: {e}", exc_info=True)
        return False, f"❌ 错误: {str(e)[:40]}"