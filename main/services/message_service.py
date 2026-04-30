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
                pass  # 继续尝试收藏夹中转
            else:
                return False, f"❌ 发送失败: {err[:50]}"
        except Exception as e:
            logger.warning(f"发送异常: {e}")
            pass  # 继续尝试收藏夹中转
        
        # 收藏夹中转
        if userbot and userbot.is_connected:
            try:
                logger.info("尝试通过收藏夹中转...")
                
                # 转发到收藏夹
                forwarded = await userbot.forward_messages(
                    chat_id="me",
                    from_chat_id=chat_id,
                    message_ids=msg_id
                )
                
                if not forwarded:
                    return False, "❌ 转发到收藏夹失败"
                
                if isinstance(forwarded, list):
                    saved_msg_id = forwarded[0].id
                else:
                    saved_msg_id = forwarded.id
                
                logger.info(f"已转发到收藏夹: msg_id={saved_msg_id}")
                
                # 尝试用 bot 从收藏夹读取
                try:
                    saved = await bot.get_messages("me", saved_msg_id)
                    if saved and not getattr(saved, 'empty', False):
                        logger.info("bot 从收藏夹读取成功，发送给用户")
                        
                        if saved.video:
                            await bot.send_video(user_id, saved.video.file_id, caption=saved.caption or "")
                        elif saved.photo:
                            await bot.send_photo(user_id, saved.photo.file_id, caption=saved.caption or "")
                        elif saved.document:
                            await bot.send_document(user_id, saved.document.file_id, caption=saved.caption or "")
                        elif saved.audio:
                            await bot.send_audio(user_id, saved.audio.file_id, caption=saved.caption or "")
                        elif saved.voice:
                            await bot.send_voice(user_id, saved.voice.file_id, caption=saved.caption or "")
                        elif saved.sticker:
                            await bot.send_sticker(user_id, saved.sticker.file_id)
                        elif saved.animation:
                            await bot.send_animation(user_id, saved.animation.file_id, caption=saved.caption or "")
                        elif saved.text:
                            await bot.send_message(user_id, saved.text)
                        
                        # 删除收藏
                        try:
                            await userbot.delete_messages("me", saved_msg_id)
                        except:
                            pass
                        
                        return True, ""
                except Exception as e:
                    logger.warning(f"bot 从收藏夹失败: {e}")
                
                # 尝试 userbot copy 给用户
                try:
                    saved = await userbot.get_messages("me", saved_msg_id)
                    if saved and not getattr(saved, 'empty', False):
                        logger.info("尝试 copy 消息给用户")
                        
                        if saved.video:
                            await userbot.send_video(user_id, saved.video.file_id, caption=saved.caption or "")
                        elif saved.photo:
                            await userbot.send_photo(user_id, saved.photo.file_id, caption=saved.caption or "")
                        elif saved.document:
                            await userbot.send_document(user_id, saved.document.file_id, caption=saved.caption or "")
                        elif saved.audio:
                            await userbot.send_audio(user_id, saved.audio.file_id, caption=saved.caption or "")
                        elif saved.voice:
                            await userbot.send_voice(user_id, saved.voice.file_id, caption=saved.caption or "")
                        elif saved.sticker:
                            await userbot.send_sticker(user_id, saved.sticker.file_id)
                        elif saved.animation:
                            await userbot.send_animation(user_id, saved.animation.file_id, caption=saved.caption or "")
                        elif saved.text:
                            await userbot.send_message(user_id, saved.text)
                        
                        # 删除收藏
                        try:
                            await userbot.delete_messages("me", saved_msg_id)
                        except:
                            pass
                        
                        return True, ""
                except Exception as e:
                    logger.error(f"userbot copy 失败: {e}")
                
                # 清理收藏
                try:
                    await userbot.delete_messages("me", saved_msg_id)
                except:
                    pass
            
            except Exception as e:
                logger.error(f"收藏夹中转失败: {e}", exc_info=True)
        
        return False, "❌ 该消息无法转发（受限内容）"
        
    except Exception as e:
        logger.error(f"异常: {e}")
        return False, f"❌ 错误: {str(e)[:40]}"