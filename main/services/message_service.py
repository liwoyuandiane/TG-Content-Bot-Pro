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
        # 检查是否有消息ID
        if len(parts) < 2 or not parts[1].isdigit():
            return None, None
        return parts[0], int(parts[1])


async def forward_message(userbot: Client, bot: Client, user_id: int, msg_link: str):
    try:
        chat_id, msg_id = parse_link(msg_link)
        
        # 检查是否成功解析
        if chat_id is None or msg_id is None:
            logger.warning(f"链接格式无效，缺少消息ID: {msg_link}")
            return False, "❌ 链接格式无效，请使用包含消息ID的链接，如：https://t.me/username/123"
        
        logger.info(f"解析: chat={chat_id}, msg={msg_id}")
        
        # 获取消息
        msg = None
        
        # 1. bot 直接获取
        try:
            msg = await bot.get_messages(chat_id, msg_id)
            if msg and not getattr(msg, 'empty', False) and (msg.video or msg.photo or msg.document or msg.audio or msg.voice or msg.sticker or msg.animation or msg.text):
                logger.info(f"bot.get_messages 成功: photo={bool(msg.photo)}, video={bool(msg.video)}")
            else:
                msg = None
        except Exception as e:
            logger.warning(f"bot.get_messages 失败: {e}")
            msg = None
        
        # 2. userbot 获取
        if not msg and userbot and userbot.is_connected:
            try:
                msg = await userbot.get_messages(chat_id, msg_id)
                if msg and not getattr(msg, 'empty', False):
                    logger.info(f"userbot.get_messages 成功: photo={bool(msg.photo)}, video={bool(msg.video)}")
                else:
                    msg = None
            except Exception as e:
                logger.warning(f"userbot.get_messages 失败: {e}")
                msg = None
        
        if not msg or getattr(msg, 'empty', False):
            if not userbot or not userbot.is_connected:
                return False, "❌ 无法访问该频道，请配置 SESSION"
            return False, "❌ 消息为空或不存在"
        
        # 尝试 bot 直接发送
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
            
            logger.info(f"发送成功")
            return True, ""
        except RPCError as e:
            err = str(e)
            logger.error(f"发送失败: {err}")
            if "MEDIA_EMPTY" in err:
                return False, "❌ 无法转发：公开群组的媒体文件无法直接获取，请尝试将机器人添加为群组成员"
            elif "PEER_ID_INVALID" in err:
                return False, "❌ 无法转发：机器人未加入该群组或频道"
            else:
                return False, f"❌ 转发失败: {err[:50]}"
        except Exception as e:
            logger.warning(f"发送异常: {e}")
            return False, "❌ 转发失败：无法获取消息内容"
        
    except Exception as e:
        logger.error(f"异常: {e}")
        return False, f"❌ 错误: {str(e)[:40]}"