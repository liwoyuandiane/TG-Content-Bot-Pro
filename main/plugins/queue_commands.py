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
            incoming=True, pattern='/queue'))
        client_manager.bot.add_event_handler(self._reset_rate, events.NewMessage(
            incoming=True, pattern='/resetrate'))
        
        self.logger.info("队列管理插件事件处理器已注册")
    
    async def on_unload(self):
        """插件卸载时移除事件处理器"""
        client_manager.bot.remove_event_handler(self._queue_status, events.NewMessage(
            incoming=True, pattern='/queue'))
        client_manager.bot.remove_event_handler(self._reset_rate, events.NewMessage(
            incoming=True, pattern='/resetrate'))
        
        self.logger.info("队列管理插件事件处理器已移除")
    
    async def _queue_status(self, event):
        """查看队列状态"""
        # 获取队列统计信息
        stats = await task_queue.get_queue_stats()
        queue_size = stats["pending_tasks"]
        running_count = stats["running_tasks"]
        current_rate = rate_limiter.rate_per_second
        
        text = "📋 **队列状态**\n\n"
        text += f"⏳ 等待中: {queue_size}\n"
        text += f"▶️  运行中: {running_count}\n"
        text += f"⚡ 当前速率: {current_rate:.1f} 请求/秒"
        
        await event.reply(text)
    
    async def _reset_rate(self, event):
        """重置速率限制器"""
        rate_limiter.rate_per_second = 0.5
        rate_limiter.flood_wait_count = 0
        rate_limiter.success_count = 0
        
        await event.reply("✅ 速率限制器已重置为初始状态 (0.5/s)")

queue_plugin = QueuePlugin()

from ..core.base_plugin import plugin_registry
plugin_registry.register(queue_plugin)