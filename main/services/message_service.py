"""消息服务模块

该模块提供消息获取和处理功能，用于从Telegram频道获取消息内容。
"""
import asyncio
import logging
import os
import time
from typing import Optional, Any

from pyrogram import Client
from pyrogram.errors import ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid, PeerIdInvalid
from telethon import TelegramClient
from ..core.database import db_manager
from ..services.traffic_service import traffic_service
from ..utils.media_utils import progress_for_pyrogram
from ..utils.file_manager import file_manager
from ..utils.error_handler import safe_execute

logger = logging.getLogger(__name__)


class MessageService:
    """消息服务
    
    负责处理Telegram消息的获取、下载和上传操作。
    """
    
    def __init__(self) -> None:
        """初始化消息服务"""
        self.db = db_manager
        self.traffic = traffic_service
    
    @safe_execute(default_return=False)
    async def get_msg(self, userbot: Client, client: Client, telethon_bot: TelegramClient, 
                      sender: int, edit_id: int, msg_link: str, offset: int = 0) -> bool:
        """获取并处理单条消息
        
        Args:
            userbot: Pyrogram用户客户端
            client: Pyrogram机器人客户端
            telethon_bot: Telethon机器人客户端
            sender: 发送者用户ID
            edit_id: 编辑消息ID
            msg_link: 消息链接
            offset: 消息ID偏移量
            
        Returns:
            bool: 处理是否成功
        """
        # 检查 userbot 是否可用
        if userbot is None:
            await client.edit_message_text(sender, edit_id, "❌ 未配置 SESSION，无法访问受限内容\n\n使用 /addsession 添加 SESSION")
            return False
        
        edit = ""
        chat = ""
        
        # 处理链接中的参数
        if "?single" in msg_link:
            msg_link = msg_link.split("?single")[0]
        
        msg_id = int(msg_link.split("/")[-1]) + offset
        
        if 't.me/c/' in msg_link or 't.me/b/' in msg_link:
            if 't.me/b/' in msg_link:
                chat = str(msg_link.split("/")[-2])
            else:
                chat = int('-100' + str(msg_link.split("/")[-2]))
            
            try:
                # 使用userbot获取消息并直接转发
                msg = await userbot.get_messages(chat, msg_id)
                
                # 检查消息类型并转发
                if msg.text:
                    # 文本消息 - 发送副本
                    edit = await client.edit_message_text(sender, edit_id, "克隆中...")
                    await client.send_message(sender, msg.text.markdown)
                    await edit.delete()
                elif msg.media:
                    # 媒体消息 - 直接转发
                    edit = await client.edit_message_text(sender, edit_id, "转发中...")
                    await userbot.forward_messages(sender, chat, msg_id)
                    await edit.delete()
                else:
                    await client.edit_message_text(sender, edit_id, "❌ 消息为空")
                    return False
                
                # 记录成功转发
                await self.db.add_forward(sender, msg_link, msg_id, str(chat), "forwarded", 0, "success")
                return True
                
            except (ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid):
                await client.edit_message_text(sender, edit_id, "您加入该频道了吗？")
                await self.db.add_forward(sender, msg_link, msg_id, str(chat), "error", 0, "failed")
                return False
            except PeerIdInvalid:
                chat = msg_link.split("/")[-3]
                try:
                    int(chat)
                    new_link = f"t.me/c/{chat}/{msg_id}"
                except ValueError:
                    new_link = f"t.me/b/{chat}/{msg_id}"
                return await self.get_msg(userbot, client, telethon_bot, sender, edit_id, new_link, offset)
            except Exception as e:
                logger.error(f"转发消息时出错: {e}", exc_info=True)
                await client.edit_message_text(sender, edit_id, f'转发失败: `{msg_link}`\n\n错误: {str(e)}')
                await self.db.add_forward(sender, msg_link, msg_id, str(chat), "error", 0, "failed")
                return False
        else:
            # 公开频道消息 - 先检查消息是否可用
            edit = await client.edit_message_text(sender, edit_id, "克隆中...")
            chat = msg_link.split("t.me")[1].split("/")[1]
            try:
                # 先获取消息检查其状态
                check_msg = await client.get_messages(chat, msg_id)
                
                if check_msg.empty:
                    # 空消息 - 尝试使用 forward_messages 作为回退
                    logger.warning(f"消息 {msg_id} 为空，尝试使用 forward_messages")
                    try:
                        await client.forward_messages(sender, chat, msg_id)
                        await self.db.add_forward(sender, msg_link, msg_id, chat, "forwarded", 0, "success")
                        await edit.delete()
                    except Exception as e:
                        logger.error(f"forward_messages 也失败: {e}")
                        await self.db.add_forward(sender, msg_link, msg_id, chat, "error", 0, "failed")
                        return await client.edit_message_text(sender, edit_id, f'❌ 消息为空或无法访问\n\n链接: `{msg_link}`')
                else:
                    # 正常消息 - 使用 copy_message
                    await client.copy_message(sender, chat, msg_id)
                    await self.db.add_forward(sender, msg_link, msg_id, chat, "copied", 0, "success")
                    await edit.delete()
            except Exception as e:
                logger.error(f"复制消息时出错: {e}", exc_info=True)
                # 记录失败
                await self.db.add_forward(sender, msg_link, msg_id, chat, "error", 0, "failed")
                return await client.edit_message_text(sender, edit_id, f'❌ 保存失败\n\n链接: `{msg_link}`\n\n错误: {str(e)}')
            
        return True
    
    def _get_file_size(self, msg: Any) -> int:
        """获取文件大小"""
        file_size = 0
        if msg.document:
            file_size = msg.document.file_size
        elif msg.video:
            file_size = msg.video.file_size
        elif msg.audio:
            file_size = msg.audio.file_size
        elif msg.photo:
            file_size = msg.photo.file_size
        elif msg.voice:
            file_size = msg.voice.file_size
        elif msg.video_note:
            file_size = msg.video_note.file_size
        return file_size
    
    def _get_thumbnail(self, sender: int) -> Optional[str]:
        """获取用户缩略图"""
        if os.path.exists(f'{sender}.jpg'):
            return f'{sender}.jpg'
        else:
            return None
    
    def _get_media_type(self, msg: Any) -> str:
        """获取媒体类型"""
        if msg.video_note:
            return "video_note"
        elif msg.video:
            return "video"
        elif msg.photo:
            return "photo"
        elif msg.document:
            return "document"
        elif msg.audio:
            return "audio"
        elif msg.voice:
            return "voice"
        else:
            return "unknown"
    
    def _translate_error(self, error_msg: str) -> str:
        """翻译常见英文错误"""
        translations = {
            "doesn't contain any downloadable media": "此消息不包含可下载的媒体文件",
            "file size": "文件大小错误",
            "timeout": "下载超时，请重试"
        }
        
        for key, value in translations.items():
            if key in error_msg.lower():
                return value
        return error_msg
    
    def _is_telethon_fallback_needed(self, error: Exception) -> bool:
        """检查是否需要使用Telethon回退上传"""
        error_str = str(error)
        return ("messages.SendMedia" in error_str or 
                "SaveBigFilePartRequest" in error_str or 
                "SendMediaRequest" in error_str or 
                "File size equals to 0 B" in error_str)
    
    async def _cleanup_file(self, file_path: str) -> bool:
        """清理临时文件"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"临时文件已清理: {file_path}")
            return True
        except Exception as e:
            logger.warning(f"清理临时文件失败 {file_path}: {e}")
            return False


# 全局消息服务实例
message_service = MessageService()