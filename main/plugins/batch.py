"""批量下载插件"""
import time
import asyncio
from typing import Dict

from ..core.base_plugin import BasePlugin
from ..core.clients import client_manager
from ..config import settings
from ..services.download_service import download_service
from ..services.download_task_manager import download_task_manager
from ..utils.media_utils import get_link
from ..utils.error_handler import handle_errors

from telethon import events, Button
from pyrogram import Client
from pyrogram.errors import FloodWait

class BatchPlugin(BasePlugin):
    """批量下载插件"""
    
    def __init__(self):
        super().__init__("batch")
        self.batch_users = set()  # 正在进行批量任务的用户
        self.batch_tasks: Dict[str, int] = {}  # 任务ID到用户ID的映射
    
    async def on_load(self):
        """插件加载时注册事件处理器"""
        # 注册命令处理器
        client_manager.bot.add_event_handler(self._cancel_command, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern='/cancel'))
        client_manager.bot.add_event_handler(self._batch_command, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern='/batch'))
        
        self.logger.info("批量下载插件事件处理器已注册")
    
    async def on_unload(self):
        """插件卸载时移除事件处理器"""
        # 移除事件处理器
        client_manager.bot.remove_event_handler(self._cancel_command, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern='/cancel'))
        client_manager.bot.remove_event_handler(self._batch_command, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern='/batch'))
        
        self.logger.info("批量下载插件事件处理器已移除")
    
    async def _cancel_command(self, event):
        """处理 /cancel 命令"""
        if event.sender_id not in self.batch_users:
            await event.reply("没有正在进行的批量任务。")
            return
        
        # 取消用户的批量任务
        for task_id, user_id in list(self.batch_tasks.items()):
            if user_id == event.sender_id:
                await download_task_manager.cancel_task(task_id)
                break
        
        self.batch_users.discard(event.sender_id)
        await event.reply("已取消。")
    
    async def _batch_command(self, event):
        """处理 /batch 命令"""
        if not event.is_private:
            return
        
        # 检查 userbot 是否可用
        if client_manager.userbot is None:
            await event.reply("❌ 未配置 SESSION，无法使用批量下载功能\n\n使用 /addsession 添加 SESSION")
            return
        
        # 检查强制订阅
        if settings.FORCESUB:
            # 这里应该实现强制订阅检查逻辑
            pass
        
        if event.sender_id in self.batch_users:
            await event.reply("您已经开始了一个批量任务，请等待它完成！")
            return
        
        async with client_manager.bot.conversation(event.chat_id) as conv:
            await conv.send_message("请回复此消息，发送您想开始保存的消息链接。", buttons=Button.force_reply())
            try:
                link_msg = await conv.get_reply()
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
            
            await conv.send_message("请回复此消息，发送您想从给定消息开始保存的文件数量/范围。", buttons=Button.force_reply())
            try:
                range_msg = await conv.get_reply()
            except Exception as e:
                self.logger.error(f"获取范围时出错: {e}")
                await conv.send_message("等待响应超时！")
                return conv.cancel()
            
            try:
                value = int(range_msg.text)
                if value > 100:
                    await conv.send_message("单次批量最多只能获取100个文件。")
                    return conv.cancel()
            except ValueError:
                await conv.send_message("范围必须是一个整数！")
                return conv.cancel()
            
            self.batch_users.add(event.sender_id)
            
            # 创建批量任务
            task_id = await download_task_manager.create_batch_task(event.sender_id, link, value)
            self.batch_tasks[task_id] = event.sender_id
            
            # 运行批量下载
            await self._run_batch(client_manager.userbot, client_manager.pyrogram_bot, 
                                event.sender_id, link, value, task_id)
            
            conv.cancel()
            self.batch_users.discard(event.sender_id)
            if task_id in self.batch_tasks:
                del self.batch_tasks[task_id]
    
    @handle_errors(default_return=False)
    async def _run_batch(self, userbot: Client, client: Client, sender: int, 
                        link: str, range_count: int, task_id: str):
        """运行批量下载任务"""
        completed = 0
        failed = 0
        
        for i in range(range_count):
            try:
                if sender not in self.batch_users:
                    await download_task_manager.complete_batch_task(task_id)
                    await client.send_message(sender, f"批量任务已完成。\n✅ 成功: {completed}\n❌ 失败: {failed}")
                    break
            except Exception as e:
                self.logger.error(f"检查批量任务状态时出错: {e}")
                await download_task_manager.complete_batch_task(task_id)
                await client.send_message(sender, f"批量任务已完成。\n✅ 成功: {completed}\n❌ 失败: {failed}")
                break
            
            try:
                # 获取速率限制许可
                # await rate_limiter.acquire()
                
                success = await download_service.download_message(userbot, client, client_manager.bot, sender, 0, link, i)
                
                if success:
                    completed += 1
                    # await rate_limiter.on_success()
                else:
                    failed += 1
                
                await download_task_manager.update_batch_progress(task_id, completed)
                
            except FloodWait as fw:
                if fw.value > 299:
                    await download_task_manager.cancel_batch_task(task_id)
                    await client.send_message(sender, f"由于洪水等待超过5分钟，取消批量任务。\n✅ 成功: {completed}\n❌ 失败: {failed}")
                    break
                
                # await rate_limiter.on_flood_wait(fw.value)
                
                try:
                    success = await download_service.download_message(userbot, client, client_manager.bot, sender, 0, link, i)
                    if success:
                        completed += 1
                    else:
                        failed += 1
                    await download_task_manager.update_batch_progress(task_id, completed)
                except Exception as retry_error:
                    self.logger.error(f"重试失败: {retry_error}")
                    failed += 1
            
            # 每5个文件或最后一批发送进度更新
            if (i + 1) % 5 == 0 or i == range_count - 1:
                progress_pct = (completed + failed) * 100 // range_count
                # current_rate = rate_limiter.rate
                progress_msg = f"📊 进度: {completed + failed}/{range_count} ({progress_pct}%)\n✅ 成功: {completed}\n❌ 失败: {failed}\n⚡ 当前速率: 0.00/s"
                
                try:
                    await client.send_message(sender, progress_msg)
                except Exception:
                    pass
        
        await download_task_manager.complete_batch_task(task_id)
        final_msg = f"🎉 批量任务完成！\n✅ 成功: {completed}\n❌ 失败: {failed}\n📊 总计: {range_count}"
        await client.send_message(sender, final_msg)


# 创建插件实例并注册
batch_plugin = BatchPlugin()

# 注册到插件注册表
from ..core.base_plugin import plugin_registry
plugin_registry.register(batch_plugin)