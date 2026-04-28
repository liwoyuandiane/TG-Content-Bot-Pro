"""批量转发插件"""
import asyncio
from typing import Dict

from ..core.base_plugin import BasePlugin
from ..core.clients import client_manager
from ..config import settings
from ..services.message_service import message_service
from ..services.tier_service import tier_service
from ..utils.media_utils import get_link
from ..utils.error_handler import safe_execute

from telethon import events, Button
from pyrogram import Client
from pyrogram.errors import FloodWait

class BatchPlugin(BasePlugin):
    """批量转发插件"""
    
    def __init__(self):
        super().__init__("batch")
        self.batch_users = set()  # 正在进行批量任务的用户
    
    async def on_load(self):
        """插件加载时注册事件处理器"""
        # 注册命令处理器 - 不再使用from_users限制，在handler内进行权限检查
        client_manager.bot.add_event_handler(self._cancel_command, events.NewMessage(
            incoming=True, pattern=r'^/cancel\b'))
        client_manager.bot.add_event_handler(self._batch_command, events.NewMessage(
            incoming=True, pattern=r'^/batch\b'))
        
        self.logger.info("批量转发插件事件处理器已注册")
    
    async def on_unload(self):
        """插件卸载时移除事件处理器"""
        # 移除事件处理器 - 不再使用from_users限制，在handler内进行权限检查
        client_manager.bot.remove_event_handler(self._cancel_command, events.NewMessage(
            incoming=True, pattern=r'^/cancel\b'))
        client_manager.bot.remove_event_handler(self._batch_command, events.NewMessage(
            incoming=True, pattern=r'^/batch\b'))
        
        self.logger.info("批量转发插件事件处理器已移除")
    
    async def _cancel_command(self, event):
        """处理 /cancel 命令"""
        if event.sender_id not in self.batch_users:
            await event.reply("没有正在进行的批量任务。")
            return
        
        # 从批量用户集合中移除
        self.batch_users.discard(event.sender_id)
        await event.reply("已取消。")
    
    async def _batch_command(self, event):
        """处理 /batch 命令"""
        if not event.is_private:
            return
        
        # 检查 userbot 是否可用
        if client_manager.userbot is None:
            await event.reply("❌ 未配置 SESSION，无法使用批量转发功能\n\n使用 /addsession 添加 SESSION")
            return
        
        # 检查强制订阅 - TODO: 需要实现完整的强制订阅检查逻辑
        # 需要使用 userbot.get_chat_member() 检查用户是否已订阅
        if settings.FORCESUB:
            # 强制订阅功能待实现：当FORCESUB配置时，检查用户是否关注了指定频道
            # 参考 start.py 中的实现方式
            self.logger.debug(f"FORCESUB配置为 {settings.FORCESUB}，跳过检查")
        
        if event.sender_id in self.batch_users:
            await event.reply("您已经开始了一个批量任务，请等待它完成！")
            return
        
        # 收集需要删除的消息ID
        messages_to_delete = [event.id]  # 用户的/batch命令
        
        async with client_manager.bot.conversation(event.chat_id) as conv:
            prompt1 = await conv.send_message("请回复此消息，发送您想开始保存的消息链接。", buttons=Button.force_reply())
            messages_to_delete.append(prompt1.id)
            
            try:
                link_msg = await conv.get_reply()
                messages_to_delete.append(link_msg.id)
                
                try:
                    link = get_link(link_msg.text)
                    if not link:
                        await conv.send_message("未找到链接。")
                        return conv.cancel()
                except Exception:
                    await conv.send_message("未找到链接。")
                    return conv.cancel()
            except Exception as e:
                self.logger.error(f"获取链接时出错: {e}")
                await conv.send_message("等待响应超时！")
                return conv.cancel()
            
            prompt2 = await conv.send_message("请回复此消息，发送您想从给定消息开始保存的文件数量/范围。", buttons=Button.force_reply())
            messages_to_delete.append(prompt2.id)
            
            try:
                range_msg = await conv.get_reply()
                messages_to_delete.append(range_msg.id)
            except Exception as e:
                self.logger.error(f"获取范围时出错: {e}")
                await conv.send_message("等待响应超时！")
                return conv.cancel()
            
            try:
                value = int(range_msg.text)
                
                # 获取用户对应的批量限制
                batch_limit = await tier_service.get_batch_limit(event.sender_id)
                is_premium = await tier_service.is_premium_user(event.sender_id)
                
                if value > batch_limit:
                    tier_name = "Premium" if is_premium else "普通用户"
                    await conv.send_message(
                        f"单次批量最多只能获取 {batch_limit} 个文件。\n"
                        f"您的当前等级：{tier_name}\n"
                        f"如需更高限额，请联系管理员升级。"
                    )
                    return conv.cancel()
            except ValueError:
                await conv.send_message("范围必须是一个整数！")
                return conv.cancel()
            
            self.batch_users.add(event.sender_id)
            
            try:
                # 直接运行批量转发（不通过任务队列）
                await self._run_batch(client_manager.userbot, client_manager.pyrogram_bot, 
                                    event.sender_id, link, value, messages_to_delete)
            finally:
                conv.cancel()
                self.batch_users.discard(event.sender_id)
    
    @safe_execute(default_return=False)
    async def _run_batch(self, userbot: Client, client: Client, sender: int,
                        link: str, range_count: int, messages_to_delete: list = None):
        """运行批量转发任务"""
        completed = 0
        failed = 0
        progress_messages = []

        async def process_message(msg_index: int) -> bool:
            nonlocal completed, failed
            progress_msg = await client.send_message(sender, "处理中...")
            try:
                success = await message_service.get_msg(userbot, client, client_manager.bot, sender, progress_msg.id, link, msg_index)
                try:
                    await progress_msg.delete()
                except Exception:
                    pass
                if success:
                    completed += 1
                else:
                    failed += 1
                return success
            except FloodWait as fw:
                try:
                    await progress_msg.delete()
                except Exception:
                    pass
                if fw.value > 299:
                    return False
                await asyncio.sleep(fw.value)
                progress_msg2 = await client.send_message(sender, "处理中...")
                try:
                    success = await message_service.get_msg(userbot, client, client_manager.bot, sender, progress_msg2.id, link, msg_index)
                    try:
                        await progress_msg2.delete()
                    except Exception:
                        pass
                    if success:
                        completed += 1
                    else:
                        failed += 1
                    return success
                except Exception as retry_error:
                    try:
                        await progress_msg2.delete()
                    except Exception:
                        pass
                    self.logger.error(f"重试失败: {retry_error}")
                    failed += 1
                    return False
            except Exception as e:
                self.logger.error(f"处理消息失败: {e}")
                failed += 1
                return False

        for i in range(range_count):
            if sender not in self.batch_users:
                final_msg = await client.send_message(sender, f"批量任务已取消。\n✅ 成功: {completed}\n❌ 失败: {failed}")
                progress_messages.append(final_msg.id)
                break

            await process_message(i)

            if (i + 1) % 5 == 0 or i == range_count - 1:
                progress_pct = (completed + failed) * 100 // range_count
                progress_msg_text = f"📊 进度: {completed + failed}/{range_count} ({progress_pct}%)\n✅ 成功: {completed}\n❌ 失败: {failed}"

                try:
                    progress_msg = await client.send_message(sender, progress_msg_text)
                    progress_messages.append(progress_msg.id)
                except Exception:
                    pass

        final_msg_text = f"🎉 批量任务完成！\n✅ 成功: {completed}\n❌ 失败: {failed}\n📊 总计: {range_count}"
        final_msg = await client.send_message(sender, final_msg_text)
        progress_messages.append(final_msg.id)

        await asyncio.sleep(5)

        try:
            if messages_to_delete:
                await client_manager.bot.delete_messages(sender, messages_to_delete)
                self.logger.info(f"已删除 {len(messages_to_delete)} 条对话消息")

            if progress_messages:
                await client.delete_messages(sender, progress_messages)
                self.logger.info(f"已删除 {len(progress_messages)} 条进度消息")

        except Exception as e:
            self.logger.error(f"删除消息时出错: {e}")


# 创建插件实例并注册
batch_plugin = BatchPlugin()

# 注册到插件注册表
from ..core.base_plugin import plugin_registry
plugin_registry.register(batch_plugin)