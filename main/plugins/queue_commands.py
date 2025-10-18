"""队列管理插件"""
from ..core.base_plugin import BasePlugin
from ..core.clients import client_manager
from ..config import settings
from ..core.task_queue import task_queue
from ..core.rate_limiter import rate_limiter
from telethon import events

class QueuePlugin(BasePlugin):
    """队列管理插件"""
    
    def __init__(self):
        super().__init__("queue")
    
    async def on_load(self):
        """插件加载时注册事件处理器"""
        client_manager.bot.add_event_handler(self._queue_status, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern='/queue'))
        client_manager.bot.add_event_handler(self._reset_rate, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern='/resetrate'))
        
        self.logger.info("队列管理插件事件处理器已注册")
    
    async def on_unload(self):
        """插件卸载时移除事件处理器"""
        client_manager.bot.remove_event_handler(self._queue_status, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern='/queue'))
        client_manager.bot.remove_event_handler(self._reset_rate, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern='/resetrate'))
        
        self.logger.info("队列管理插件事件处理器已移除")
    
    async def _queue_status(self, event):
        """查看队列状态"""
        queue_size = task_queue.get_queue_size()
        running_count = task_queue.get_running_count()
        available_tokens = rate_limiter.get_available_tokens()
        current_rate = rate_limiter.rate
        
        text = "📋 **队列状态**\n\n"
        text += f"⏳ 等待中: {queue_size}\n"
        text += f"▶️  运行中: {running_count}\n"
        text += f"⚡ 当前速率: {current_rate:.2f} 请求/秒\n"
        text += f"🎫 可用令牌: {available_tokens:.2f}\n"
        text += f"📊 FloodWait次数: {rate_limiter.flood_wait_count}\n"
        text += f"✅ 成功次数: {rate_limiter.success_count}\n"
        
        await event.reply(text)
    
    async def _reset_rate(self, event):
        """重置速率限制器"""
        rate_limiter.rate = 0.5
        rate_limiter.flood_wait_count = 0
        rate_limiter.success_count = 0
        
        await event.reply("✅ 速率限制器已重置为初始状态 (0.5/s)")

queue_plugin = QueuePlugin()

from ..core.base_plugin import plugin_registry
plugin_registry.register(queue_plugin)