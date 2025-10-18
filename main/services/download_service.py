"""下载服务模块

该模块提供消息下载和文件处理功能，支持从Telegram频道下载各种类型的媒体文件。
"""
import asyncio
import logging
import os
import time
from typing import Optional, Tuple, Any, Union

from pyrogram import Client
from pyrogram.errors import ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid, PeerIdInvalid
from pyrogram.enums import MessageMediaType
from telethon import TelegramClient
from telethon.tl.types import DocumentAttributeVideo
from ethon.pyfunc import video_metadata
from ethon.telefunc import fast_upload

from ..core.database import DatabaseManager
from ..services.traffic_service import TrafficService
from ..utils.media_utils import screenshot, progress_for_pyrogram
from ..utils.file_manager import file_manager
from ..utils.error_handler import handle_errors
from ..exceptions.telegram import ChannelAccessException, SessionException
from ..exceptions.validation import TrafficLimitException

logger = logging.getLogger(__name__)


class DownloadService:
    """下载服务
    
    负责处理Telegram消息的下载、文件处理和上传操作。
    支持多种媒体类型和不同的上传策略。
    """
    
    def __init__(self) -> None:
        """初始化下载服务"""
        self.db: DatabaseManager = db_manager
        self.traffic: TrafficService = traffic_service
    
    @handle_errors(default_return=False)
    async def download_message(self, userbot: Client, client: Client, telethon_bot: TelegramClient, 
                              sender: int, edit_id: int, msg_link: str, offset: int = 0) -> bool:
        """下载单条消息
        
        Args:
            userbot: Pyrogram用户客户端
            client: Pyrogram机器人客户端
            telethon_bot: Telethon机器人客户端
            sender: 发送者用户ID
            edit_id: 编辑消息ID
            msg_link: 消息链接
            offset: 消息ID偏移量
            
        Returns:
            bool: 下载是否成功
        """
        # 检查 userbot 是否可用
        if userbot is None:
            await client.edit_message_text(sender, edit_id, "❌ 未配置 SESSION，无法访问受限内容\n\n使用 /addsession 添加 SESSION")
            return False
        
        edit = ""
        chat = ""
        round_message = False
        
        # 处理链接中的参数
        if "?single" in msg_link:
            msg_link = msg_link.split("?single")[0]
        
        msg_id = int(msg_link.split("/")[-1]) + offset
        height, width, duration, thumb_path = 90, 90, 0, None
        
        if 't.me/c/' in msg_link or 't.me/b/' in msg_link:
            if 't.me/b/' in msg_link:
                chat = str(msg_link.split("/")[-2])
            else:
                chat = int('-100' + str(msg_link.split("/")[-2]))
            
            file = ""
            try:
                msg = await userbot.get_messages(chat, msg_id)
                if msg.media:
                    if msg.media == MessageMediaType.WEB_PAGE:
                        edit = await client.edit_message_text(sender, edit_id, "克隆中...")
                        if msg.text:
                            await client.send_message(sender, msg.text.markdown)
                        await edit.delete()
                        return True
                
                if not msg.media:
                    if msg.text:
                        edit = await client.edit_message_text(sender, edit_id, "克隆中...")
                        await client.send_message(sender, msg.text.markdown)
                        await edit.delete()
                        return True
                    else:
                        await client.edit_message_text(sender, edit_id, "❌ 消息为空")
                        return False
                
                edit = await client.edit_message_text(sender, edit_id, "尝试下载...")
                
                # 获取文件大小并检查流量限制
                file_size = self._get_file_size(msg)
                
                # 检查流量限制
                can_download, limit_msg = await self.traffic.check_traffic_limit(sender, file_size)
                if not can_download:
                    await client.edit_message_text(sender, edit_id, f"❌ {limit_msg}\n\n使用 /traffic 查看流量使用情况")
                    await self.db.add_download(sender, msg_link, msg_id, str(chat), "限制", file_size, "failed")
                    return False
                
                file = await userbot.download_media(
                    msg,
                    progress=progress_for_pyrogram,
                    progress_args=(
                        client,
                        "**DOWNLOADING:**\n",
                        edit,
                        time.time()
                    )
                )
                
                if not file or not os.path.exists(file):
                    await client.edit_message_text(sender, edit_id, "❌ 下载失败")
                    await self.db.add_download(sender, msg_link, msg_id, str(chat), "download_error", file_size, "failed")
                    return False
                    
                logger.info(f"下载完成: {file}")
                await client.edit_message_text(sender, edit_id, '准备上传！')
                
                caption = None
                if msg.caption is not None:
                    caption = msg.caption
                
                if msg.media == MessageMediaType.VIDEO_NOTE:
                    round_message = True
                    logger.info("获取视频元数据")
                    data = video_metadata(file)
                    height, width, duration = data["height"], data["width"], data["duration"]
                    logger.info(f'视频信息: 时长={duration}, 宽={width}, 高={height}')
                    try:
                        thumb_path = await screenshot(file, duration, sender)
                    except Exception:
                        thumb_path = None
                    await client.send_video_note(
                        chat_id=sender,
                        video_note=file,
                        length=height, duration=duration, 
                        thumb=thumb_path,
                        progress=progress_for_pyrogram,
                        progress_args=(
                            client,
                            '**UPLOADING:**\n',
                            edit,
                            time.time()
                        )
                    )
                elif msg.media == MessageMediaType.VIDEO and msg.video.mime_type in ["video/mp4", "video/x-matroska"]:
                    logger.info("获取视频元数据")
                    data = video_metadata(file)
                    height, width, duration = data["height"], data["width"], data["duration"]
                    logger.info(f'视频信息: 时长={duration}, 宽={width}, 高={height}')
                    try:
                        thumb_path = await screenshot(file, duration, sender)
                    except Exception:
                        thumb_path = None
                    await client.send_video(
                        chat_id=sender,
                        video=file,
                        caption=caption,
                        supports_streaming=True,
                        height=height, width=width, duration=duration, 
                        thumb=thumb_path,
                        progress=progress_for_pyrogram,
                        progress_args=(
                            client,
                            '**UPLOADING:**\n',
                            edit,
                            time.time()
                        )
                    )
                elif msg.media == MessageMediaType.PHOTO:
                    await edit.edit("上传照片中...")
                    await telethon_bot.send_file(sender, file, caption=caption)
                else:
                    thumb_path = self._get_thumbnail(sender)
                    await client.send_document(
                        sender,
                        file, 
                        caption=caption,
                        thumb=thumb_path,
                        progress=progress_for_pyrogram,
                        progress_args=(
                            client,
                            '**UPLOADING:**\n',
                            edit,
                            time.time()
                        )
                    )
                
                # 清理文件
                await self._cleanup_file(file)
                
                # 记录流量和下载成功
                media_type = self._get_media_type(msg)
                await self.traffic.add_traffic(sender, file_size, file_size)
                await self.db.add_download(sender, msg_link, msg_id, str(chat), media_type, file_size, "success")
                
                await edit.delete()
                return True
                
            except (ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid) as e:
                logger.warning(f"频道访问错误: {e}")
                await client.edit_message_text(sender, edit_id, "您加入该频道了吗？")
                await self.db.add_download(sender, msg_link, msg_id, str(chat), "channel_error", 0, "failed")
                return False
            except PeerIdInvalid:
                chat = msg_link.split("/")[-3]
                try:
                    int(chat)
                    new_link = f"t.me/c/{chat}/{msg_id}"
                except ValueError:
                    new_link = f"t.me/b/{chat}/{msg_id}"
                return await self.download_message(userbot, client, telethon_bot, sender, edit_id, new_link, 0)
            except Exception as e:
                logger.error(f"下载消息时出错: {e}", exc_info=True)
                if self._is_telethon_fallback_needed(e):
                    return await self._upload_with_telethon_fallback(
                        userbot, client, telethon_bot, sender, edit_id, msg_link, 
                        msg, file, chat, msg_id, file_size, edit, round_message, 
                        height, width, duration, thumb_path, caption
                    )
                else:
                    error_msg = self._translate_error(str(e))
                    await client.edit_message_text(sender, edit_id, f'保存失败: `{msg_link}`\n\n错误: {error_msg}')
                    await self.db.add_download(sender, msg_link, msg_id, str(chat), "error", file_size, "failed")
                    await self._cleanup_file(file)
                    return False
        else:
            return await self._download_public_message(client, sender, edit_id, msg_link, msg_id)
    
    def _get_file_size(self, msg: Any) -> int:
        """获取文件大小
        
        Args:
            msg: Telegram消息对象
            
        Returns:
            int: 文件大小（字节）
        """
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
        """获取缩略图路径
        
        Args:
            sender: 发送者用户ID
            
        Returns:
            Optional[str]: 缩略图文件路径，如果不存在则返回None
        """
        if os.path.exists(f'{sender}.jpg'):
            return f'{sender}.jpg'
        else:
            return None
    
    def _get_media_type(self, msg: Any) -> str:
        """获取媒体类型
        
        Args:
            msg: Telegram消息对象
            
        Returns:
            str: 媒体类型字符串
        """
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
        """翻译常见错误信息
        
        Args:
            error_msg: 原始错误信息
            
        Returns:
            str: 翻译后的错误信息
        """
        if "doesn't contain any downloadable media" in error_msg:
            return "此消息不包含可下载的媒体文件"
        elif "file size" in error_msg.lower():
            return "文件大小错误"
        elif "timeout" in error_msg.lower():
            return "下载超时，请重试"
        elif "FloodWait" in error_msg:
            return "请求过于频繁，请稍后再试"
        else:
            return error_msg
    
    def _is_telethon_fallback_needed(self, error: Exception) -> bool:
        """判断是否需要使用Telethon回退上传
        
        Args:
            error: 异常对象
            
        Returns:
            bool: 是否需要回退上传
        """
        error_str = str(error)
        return ("messages.SendMedia" in error_str or 
                "SaveBigFilePartRequest" in error_str or 
                "SendMediaRequest" in error_str or 
                error_str == "File size equals to 0 B")
    
    async def _upload_with_telethon_fallback(self, userbot: Client, client: Client, telethon_bot: TelegramClient, 
                                           sender: int, edit_id: int, msg_link: str, msg: Any, file: str, 
                                           chat: str, msg_id: int, file_size: int, edit: Any, 
                                           round_message: bool, height: int, width: int, duration: int,
                                           thumb_path: Optional[str], caption: Optional[str]) -> bool:
        """使用Telethon回退上传
        
        Args:
            userbot: Pyrogram用户客户端
            client: Pyrogram机器人客户端
            telethon_bot: Telethon机器人客户端
            sender: 发送者用户ID
            edit_id: 缩略图路径
            caption: 文件说明
            
        Returns:
            bool: 上传是否成功
        """
        try:
            if msg.media == MessageMediaType.VIDEO and msg.video.mime_type in ["video/mp4", "video/x-matroska"]:
                UT = time.time()
                uploader = await fast_upload(f'{file}', f'{file}', UT, telethon_bot, edit, '**UPLOADING:**')
                attributes = [DocumentAttributeVideo(duration=duration, w=width, h=height, round_message=round_message, supports_streaming=True)] 
                await telethon_bot.send_file(sender, uploader, caption=caption, thumb=thumb_path, attributes=attributes, force_document=False)
            elif msg.media == MessageMediaType.VIDEO_NOTE:
                uploader = await fast_upload(f'{file}', f'{file}', UT, telethon_bot, edit, '**UPLOADING:**')
                attributes = [DocumentAttributeVideo(duration=duration, w=width, h=height, round_message=round_message, supports_streaming=True)] 
                await telethon_bot.send_file(sender, uploader, caption=caption, thumb=thumb_path, attributes=attributes, force_document=False)
            else:
                UT = time.time()
                uploader = await fast_upload(f'{file}', f'{file}', UT, telethon_bot, edit, '**UPLOADING:**')
                await telethon_bot.send_file(sender, uploader, caption=caption, thumb=thumb_path, force_document=True)
            
            await self._cleanup_file(file)
            
            # 记录流量和下载成功（Telethon上传）
            media_type = "video" if msg.video else "document"
            await self.traffic.add_traffic(sender, file_size, file_size)
            await self.db.add_download(sender, msg_link, msg_id, str(chat), media_type, file_size, "success")
            await edit.delete()
            return True
            
        except Exception as e:
            logger.error(f"使用Telethon上传时出错: {e}", exc_info=True)
            error_msg = self._translate_error(str(e))
            await client.edit_message_text(sender, edit_id, f'保存失败: `{msg_link}`\n\n错误: {error_msg}')
            await self.db.add_download(sender, msg_link, msg_id, str(chat), "error", file_size, "failed")
            await self._cleanup_file(file)
            return False
    
    async def _download_public_message(self, client: Client, sender: int, edit_id: int, 
                                     msg_link: str, msg_id: int) -> bool:
        """下载公开消息
        
        Args:
            client: Pyrogram客户端
            sender: 发送者用户ID
            edit_id: 编辑消息ID
            msg_link: 消息链接
            msg_id: 消息ID
            
        Returns:
            bool: 下载是否成功
        """
        edit = await client.edit_message_text(sender, edit_id, "克隆中...")
        chat = msg_link.split("t.me")[1].split("/")[1]
        try:
            msg = await client.get_messages(chat, msg_id)
            if msg.empty:
                new_link = f't.me/b/{chat}/{int(msg_id)}'
                return await self.download_message(None, client, None, sender, edit_id, new_link, 0)
            await client.copy_message(sender, chat, msg_id)
        except Exception as e:
            logger.error(f"复制消息时出错: {e}", exc_info=True)
            return await client.edit_message_text(sender, edit_id, f'保存失败: `{msg_link}`\n\n错误: {str(e)}')
        await edit.delete()
        return True
    
    @handle_errors(default_return=False)
    async def _cleanup_file(self, file_path: str) -> bool:
        """清理下载的文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 清理是否成功
        """
        try:
            if file_manager.file_exists(file_path):
                file_manager.safe_remove(file_path)
                logger.info(f"已清理文件: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"清理文件时出错: {e}", exc_info=True)
            return False


# 全局下载服务实例
from ..core.database import db_manager
from ..services.traffic_service import traffic_service
download_service = DownloadService()