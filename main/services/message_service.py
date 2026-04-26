"""消息服务模块"""
import logging
from typing import Optional

from pyrogram import Client
from pyrogram.errors import ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid, PeerIdInvalid
from telethon import TelegramClient
from ..core.database import db_manager
from ..utils.error_handler import safe_execute

logger = logging.getLogger(__name__)


class MessageService:
    """消息服务
    
    负责处理Telegram消息的获取、下载和上传操作。
    """
    
    def __init__(self) -> None:
        """初始化消息服务"""
        self.db = db_manager
    
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


message_service = MessageService()