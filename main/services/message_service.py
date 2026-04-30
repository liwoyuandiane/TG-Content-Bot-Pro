"""消息服务 - 智能获取方案"""
import logging
import asyncio

from pyrogram import Client
from pyrogram.errors import RPCError, FloodWait, Forbidden
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
            if not userbot or not userbot.is_connected:
                return False, "❌ 无法访问该频道，请配置 SESSION 或将机器人添加到频道"
            return False, "❌ 消息为空或不存在"
        
        # 方案A: bot 直接发送
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
            return True, ""
        except RPCError as e:
            err = str(e)
            logger.error(f"发送失��: {err}")
            if "MEDIA_EMPTY" not in err:
                return False, f"❌ 发送失败: {err[:50]}"
        
        # 方案B: 通过收藏夹中转（私有频道）
        if userbot and userbot.is_connected:
            try:
                logger.info("尝试通过收藏夹中转...")
                
                # 1. 转发到收藏夹
                forwarded = await userbot.forward_messages(
                    chat_id="me",
                    from_chat_id=chat_id,
                    message_ids=msg_id
                )
                
                if not forwarded:
                    return False, "❌ 转发到收藏夹失败"
                
                # 获取转发后的消息ID
                if isinstance(forwarded, list):
                    saved_msg = forwarded[0]
                else:
                    saved_msg = forwarded
                
                saved_msg_id = saved_msg.id
                logger.info(f"已转发到收藏夹: msg_id={saved_msg_id}")
                
                # 2. 先尝试用 bot 从收藏夹获取并发送
                try:
                    saved_in_bot = await bot.get_messages("me", saved_msg_id)
                    
                    if saved_in_bot and not getattr(saved_in_bot, 'empty', False):
                        logger.info(f"bot.get_messages 从收藏夹成功")
                        
                        # bot 发送给用户
                        if saved_in_bot.video:
                            await bot.send_video(user_id, saved_in_bot.video.file_id, caption=saved_in_bot.caption or "")
                        elif saved_in_bot.photo:
                            await bot.send_photo(user_id, saved_in_bot.photo.file_id, caption=saved_in_bot.caption or "")
                        elif saved_in_bot.document:
                            await bot.send_document(user_id, saved_in_bot.document.file_id, caption=saved_in_bot.caption or "")
                        elif saved_in_bot.audio:
                            await bot.send_audio(user_id, saved_in_bot.audio.file_id, caption=saved_in_bot.caption or "")
                        elif saved_in_bot.voice:
                            await bot.send_voice(user_id, saved_in_bot.voice.file_id, caption=saved_in_bot.caption or "")
                        elif saved_in_bot.sticker:
                            await bot.send_sticker(user_id, saved_in_bot.sticker.file_id)
                        elif saved_in_bot.animation:
                            await bot.send_animation(user_id, saved_in_bot.animation.file_id, caption=saved_in_bot.caption or "")
                        elif saved_in_bot.text:
                            await bot.send_message(user_id, saved_in_bot.text)
                        
                        # 删除收藏夹消息
                        try:
                            await userbot.delete_messages("me", saved_msg_id)
                            logger.info("收藏夹消息已删除")
                        except:
                            pass
                        
                        logger.info(f"通过收藏夹发送成功: {msg_link}")
                        return True, ""
                except Exception as e:
                    logger.warning(f"bot 无法从收藏夹获取: {e}")
                
                # 3. bot 失败，用 userbot 直接从收藏夹转发给用户
                try:
                    await userbot.forward_messages(
                        chat_id=user_id,
                        from_chat_id="me",
                        message_ids=saved_msg_id
                    )
                    logger.info(f"userbot 从收藏夹转发成功")
                    
                    # 删除收藏夹消息
                    try:
                        await userbot.delete_messages("me", saved_msg_id)
                        logger.info("收藏夹消息已删除")
                    except:
                        pass
                    
                    return True, ""
                except Exception as e:
                    logger.error(f"userbot 从收藏夹转发失败: {e}")
                    # 尝试删除收藏夹消息
                    try:
                        await userbot.delete_messages("me", saved_msg_id)
                    except:
                        pass
            
            except Exception as e:
                logger.error(f"收藏夹中转失败: {e}", exc_info=True)
        
        return False, "❌ 该消息无法转发（可能是受限内容）"
        
    except Exception as e:
        logger.error(f"异常: {e}")
        return False, f"❌ 错误: {str(e)[:40]}"