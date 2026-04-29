"""消息服务 - 智能获取方案"""
import logging

from pyrogram import Client
from pyrogram.errors import RPCError
from ..core.database import db_manager

logger = logging.getLogger(__name__)


def parse_link(msg_link: str):
    msg_link = msg_link.strip()
    if "?single" in msg_link:
        msg_link = msg_link.split("?single")[0]
    
    if '/c/' in msg_link:
        parts = msg_link.split('/c/')[1].split('/')
        return int('-100' + parts[0]), int(parts[1])
    else:
        parts = msg_link.split('t.me/')[1].split('/')
        return parts[0], int(parts[1])


async def forward_message(userbot: Client, bot: Client, user_id: int, msg_link: str):
    try:
        chat_id, msg_id = parse_link(msg_link)
        logger.info(f"解析: chat={chat_id}, msg={msg_id}")
        
        # 方案1: 尝试 bot 直接获取（公开频道/群组）
        msg = None
        try:
            msg = await bot.get_messages(chat_id, msg_id)
            if msg and not getattr(msg, 'empty', False) and (msg.video or msg.photo or msg.document or msg.audio or msg.voice or msg.sticker or msg.animation or msg.text):
                logger.info(f"bot.get_messages 成功: video={bool(msg.video)}, photo={bool(msg.photo)}")
            else:
                msg = None
        except Exception as e:
            logger.warning(f"bot.get_messages 失败: {e}")
            msg = None
        
        # 方案2: 用 userbot 获取
        if not msg and userbot and userbot.is_connected:
            try:
                msg = await userbot.get_messages(chat_id, msg_id)
                if msg and not getattr(msg, 'empty', False) and (msg.video or msg.photo or msg.document or msg.audio or msg.voice or msg.sticker or msg.animation or msg.text):
                    logger.info(f"userbot.get_messages 成功: video={bool(msg.video)}, photo={bool(msg.photo)}")
                else:
                    msg = None
            except Exception as e:
                logger.warning(f"userbot.get_messages 失败: {e}")
                msg = None
        
        if not msg or getattr(msg, 'empty', False):
            return False, "❌ 消息为空或不存在"
        
        # 用 bot 发送
        try:
            if msg.video:
                await bot.send_video(user_id, msg.video.file_id, caption=msg.caption or "")
            elif msg.photo:
                await bot.send_photo(user_id, msg.photo.file_id, caption=msg.caption or "")
            elif msg.document:
                await bot.send_document(user_id, msg.document.file_id, caption=msg.caption or "")
            elif msg.audio:
                await bot.send_audio(user_id, msg.audio.file_id, caption=msg.caption or "")
            elif msg.voice:
                await bot.send_voice(user_id, msg.voice.file_id, caption=msg.caption or "")
            elif msg.sticker:
                await bot.send_sticker(user_id, msg.sticker.file_id)
            elif msg.animation:
                await bot.send_animation(user_id, msg.animation.file_id, caption=msg.caption or "")
            elif msg.text:
                await bot.send_message(user_id, msg.text)
            else:
                return False, "❌ 不支持的消息类型"
            
            logger.info(f"发送成功: {msg_link}")
            return True, ""  # 成功不返回消息
        except RPCError as e:
            err = str(e)
            logger.error(f"发送失败: {err}")
            if "MEDIA_EMPTY" in err:
                return False, "❌ 该消息无法转发（可能是受限内容）"
            return False, f"❌ 发送失败: {err[:50]}"
        except Exception as e:
            logger.error(f"发送异常: {e}")
            return False, f"❌ 错误: {str(e)[:40]}"
        
    except Exception as e:
        logger.error(f"异常: {e}")
        return False, f"❌ 错误: {str(e)[:40]}"