"""消息服务 - 智能获取与转发方案

核心策略(参考 Save-Restricted-Content-Bot-v3 / SaveRestrictedContentBot 的成熟实现):
1. 先尝试 bot 直接使用 file_id 发送(公开频道:快、省流量)
2. 失败(MEDIA_EMPTY 等,常见于受限内容/私有频道:userbot 获取的 file_id
   在 bot 侧不通用)时,降级为 userbot 下载媒体到本地,再由 bot 重新上传
3. 覆盖全部媒体类型:video / video_note / photo / document / audio / voice /
   sticker / animation / text
"""
import logging
import os
import re
import time

from pyrogram import Client
from pyrogram.errors import RPCError
from pyrogram.enums import MessageMediaType

from ..utils.file_manager import file_manager

logger = logging.getLogger(__name__)

# 视频/音频扩展名:document 类型消息按扩展名识别为视频或音频
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv',
                    '.webm', '.m4v', '.3gp', '.ogv', '.ts'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma',
                    '.m4a', '.opus', '.aiff', '.ac3'}

# 发送 RPC 失败时可降级为下载重传的错误关键字
REDOWNLOAD_ERROR_KEYWORDS = (
    "MEDIA_EMPTY",
    "FILE_REFERENCE_EXPIRED",
    "FILE_REFERENCE_EMPTY",
    "CHANNEL_INVALID",
    "MESSAGE_ID_INVALID",
    "MEDIA_INVALID",
)


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


async def get_message_any(client: Client, chat_id, msg_id):
    """尝试从一个客户端获取消息

    Returns:
        (msg, client) - 成功返回消息对象和来源客户端;失败返回 (None, None)
    """
    try:
        msg = await client.get_messages(chat_id, msg_id)
        if msg and not getattr(msg, 'empty', False):
            return msg, client
        return None, None
    except Exception as e:
        logger.warning(f"{client.name}.get_messages 失败: {e}")
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


def _media_file_id(msg) -> str:
    """获取消息媒体对应的 file_id(photo 取最大分辨率)"""
    if msg.video:
        return msg.video.file_id
    if msg.video_note:
        return msg.video_note.file_id
    if msg.photo:
        return msg.photo.file_id
    if msg.document:
        return msg.document.file_id
    if msg.audio:
        return msg.audio.file_id
    if msg.voice:
        return msg.voice.file_id
    if msg.sticker:
        return msg.sticker.file_id
    if msg.animation:
        return msg.animation.file_id
    return None


def _download_file_name(msg, fallback_ext: str = "") -> str:
    """构造下载文件名,尽量保留原始扩展名

    Pyrogram 的 download_media 若给 file_name 不带扩展名,下载出的文件将
    没有扩展名,导致后续按扩展名识别媒体类型失败(视频变文档发送)。
    这里优先使用消息自带的文件名,否则按媒体类型补全扩展名。
    """
    ts = int(time.time())

    # 从消息中提取原始文件名(带扩展名)
    original = None
    if msg.document and msg.document.file_name:
        original = msg.document.file_name
    elif msg.video and msg.video.file_name:
        original = msg.video.file_name
    elif msg.audio and msg.audio.file_name:
        original = msg.audio.file_name

    if original:
        base = os.path.basename(original)[:80]
        return f"temp/{ts}_{base}"

    if msg.video or msg.video_note or msg.animation:
        ext = ".mp4"
    elif msg.photo:
        ext = ".jpg"
    elif msg.audio:
        ext = ".mp3"
    elif msg.voice:
        ext = ".ogg"
    elif msg.document:
        ext = fallback_ext or ".bin"
    else:
        ext = ".bin"
    return f"temp/{ts}{ext}"


def _send_func_for(msg, bot: Client, user_id: int, file_id: str, caption: str):
    """根据消息媒体类型选择对应的发送方法(file_id 方式)

    Returns:
        (coroutine, kwargs) 或 None(纯文本或不可识别)
    """
    kwargs = {}
    if msg.video:
        m = msg.video
        kwargs = dict(duration=m.duration, width=m.width, height=m.height,
                      caption=caption or m.caption or "")
        return bot.send_video(user_id, file_id, **kwargs), kwargs
    if msg.video_note:
        m = msg.video_note
        kwargs = dict(duration=m.duration, length=m.length)
        return bot.send_video_note(user_id, file_id, **kwargs), kwargs
    if msg.photo:
        return bot.send_photo(user_id, file_id, caption=caption or msg.caption or ""), {}
    if msg.audio:
        m = msg.audio
        kwargs = dict(duration=m.duration, performer=m.performer,
                      title=m.title, caption=caption or msg.caption or "")
        return bot.send_audio(user_id, file_id, **kwargs), kwargs
    if msg.voice:
        m = msg.voice
        kwargs = dict(duration=m.duration, caption=caption or msg.caption or "")
        return bot.send_voice(user_id, file_id, **kwargs), kwargs
    if msg.sticker:
        return bot.send_sticker(user_id, file_id), {}
    if msg.animation:
        m = msg.animation
        kwargs = dict(duration=m.duration, width=m.width, height=m.height,
                      caption=caption or msg.caption or "")
        return bot.send_animation(user_id, file_id, **kwargs), kwargs
    if msg.document:
        m = msg.document
        kwargs = dict(file_name=m.file_name, caption=caption or msg.caption or "")
        return bot.send_document(user_id, file_id, **kwargs), kwargs
    return None, None


def _detect_media_type(msg, file_path: str) -> str:
    """检测本地文件的媒体类型(document 按扩展名识别为视频/音频)"""
    ext = os.path.splitext(file_path)[1].lower()
    if msg.video or (msg.document and ext in VIDEO_EXTENSIONS):
        return "video"
    if msg.video_note:  # noqa: SIM102
        return "video_note"
    if msg.audio or (msg.document and ext in AUDIO_EXTENSIONS):
        return "audio"
    if msg.photo:
        return "photo"
    if msg.voice:
        return "voice"
    if msg.sticker:
        return "sticker"
    if msg.animation:
        return "animation"
    return "document"


async def _send_local_file(bot: Client, user_id: int, msg, file_path: str,
                           caption: str) -> bool:
    """用本地文件发送(下载重传路径)"""
    mtype = _detect_media_type(msg, file_path)
    caption = caption or (msg.caption or "")

    try:
        if mtype == "video":
            m = getattr(msg, 'video', None)
            kwargs = dict(caption=caption, supports_streaming=True)
            if m:
                kwargs.update(duration=m.duration, width=m.width, height=m.height)
            await bot.send_video(user_id, video=file_path, **kwargs)
        elif mtype == "video_note":
            m = getattr(msg, 'video_note', None)
            kwargs = {}
            if m:
                kwargs.update(duration=m.duration, length=m.length)
            await bot.send_video_note(user_id, video_note=file_path, **kwargs)
        elif mtype == "audio":
            m = getattr(msg, 'audio', None)
            kwargs = dict(caption=caption)
            if m:
                kwargs.update(duration=m.duration, performer=m.performer,
                              title=m.title)
            await bot.send_audio(user_id, audio=file_path, **kwargs)
        elif mtype == "photo":
            await bot.send_photo(user_id, photo=file_path, caption=caption)
        elif mtype == "voice":
            await bot.send_voice(user_id, voice=file_path, caption=caption)
        elif mtype == "sticker":
            await bot.send_sticker(user_id, sticker=file_path)
        elif mtype == "animation":
            m = getattr(msg, 'animation', None)
            kwargs = dict(caption=caption)
            if m:
                kwargs.update(duration=m.duration, width=m.width, height=m.height)
            await bot.send_animation(user_id, animation=file_path, **kwargs)
        else:  # document
            await bot.send_document(user_id, document=file_path, caption=caption)
        return True
    except RPCError as e:
        logger.error(f"本地文件发送失败: {e}")
        return False
    except Exception as e:
        logger.error(f"本地文件发送异常: {e}")
        return False


async def forward_message(userbot: Client, bot: Client, user_id: int, msg_link: str):
    """转发 Telegram 消息给用户

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

        # 获取消息:先 bot, 后 userbot
        msg = None
        src = None

        if bot and bot.is_connected:
            msg, src = await get_message_any(bot, chat_id, msg_id)
            if msg:
                logger.info(f"bot.get_messages 成功: chat={chat_id}")

        if not msg and userbot and userbot.is_connected:
            msg, src = await get_message_any(userbot, chat_id, msg_id)
            if msg:
                logger.info(f"userbot.get_messages 成功: chat={chat_id}")

        # 消息不存在或为空
        if not msg or getattr(msg, 'empty', False):
            if not userbot or not userbot.is_connected:
                return False, "❌ 无法访问该频道，请配置 SESSION"
            return False, "❌ 消息为空或不存在"

        if not _is_sendable(msg):
            return False, "❌ 消息为空或不存在"

        # 纯文本消息直接发送
        if not msg.media and msg.text:
            await bot.send_message(user_id, msg.text)
            logger.info("文本消息发送成功")
            return True, ""

        caption = msg.caption or ""

        # 策略1: bot 直接使用 file_id 发送(公开频道, 快)
        file_id = _media_file_id(msg)
        if file_id:
            try:
                send_coro, _ = _send_func_for(msg, bot, user_id, file_id, caption)
                if send_coro:
                    await send_coro
                    logger.info("file_id 发送成功")
                    return True, ""
            except RPCError as e:
                err = str(e)
                logger.error(f"file_id 发送失败: {err}")
                # 受限内容等场景, 降级为下载重传
                if not any(kw in err for kw in REDOWNLOAD_ERROR_KEYWORDS):
                    return False, f"❌ 转发失败: {err[:50]}"
            except Exception as e:
                logger.error(f"file_id 发送异常: {e}")

        # 策略2: userbot 下载媒体到本地, bot 重新上传(受限内容核心方案)
        if src and src.is_connected:
            logger.info("🔄 降级方案: 下载媒体后重新上传...")
            file_path = None
            try:
                download_name = _download_file_name(msg)
                os.makedirs("temp", exist_ok=True)
                file_path = await src.download_media(
                    msg,
                    file_name=download_name,
                )
                if file_path and os.path.exists(file_path):
                    logger.info(f"下载完成: {file_path} ({os.path.getsize(file_path)} bytes)")
                    ok = await _send_local_file(bot, user_id, msg, file_path, caption)
                    if ok:
                        return True, ""
                    return False, "❌ 转发失败：媒体发送失败"
                logger.warning("下载媒体失败或文件不存在")
                return False, "❌ 转发失败：无法下载媒体内容"
            except Exception as e:
                logger.error(f"下载重传失败: {e}")
                return False, f"❌ 转发失败：{str(e)[:40]}"
            finally:
                # 清理临时文件
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logger.info(f"已清理临时文件: {file_path}")
                    except Exception as e:
                        logger.warning(f"清理临时文件失败: {e}")

        return False, "❌ 转发失败：无法获取消息内容"

    except Exception as e:
        logger.error(f"forward_message 异常: {e}", exc_info=True)
        return False, f"❌ 错误: {str(e)[:40]}"
