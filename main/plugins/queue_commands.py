"""队列管理插件"""
from ..core.base_plugin import BasePlugin
from ..core.clients import client_manager
from ..core.rate_limiter import rate_limiter
from telethon import events


class QueueStats:
    """轻量级队列状态（无任务队列功能）"""
    pending_tasks = 0
    running_tasks = 0

    @staticmethod
    async def get_queue_stats():
        return {
            "pending_tasks": QueueStats.pending_tasks,
            "running_tasks": QueueStats.running_tasks,
            "completed_tasks": 0,
            "workers": 0,
            "stats": {"total_tasks": 0, "completed_tasks": 0, "failed_tasks": 0, "cancelled_tasks": 0}
        }


task_queue = QueueStats()


class QueuePlugin(BasePlugin):
    """队列管理插件"""

    def __init__(self):
        super().__init__("queue")

    async def on_load(self):
        client_manager.bot.add_event_handler(self._queue_status, events.NewMessage(
            incoming=True, pattern=r'^/queue\b'))
        client_manager.bot.add_event_handler(self._reset_rate, events.NewMessage(
            incoming=True, pattern=r'^/resetrate\b'))
        self.logger.info("队列管理插件事件处理器已注册")
    
    async def on_unload(self):
        client_manager.bot.remove_event_handler(self._queue_status, events.NewMessage(
            incoming=True, pattern=r'^/queue\b'))
        client_manager.bot.remove_event_handler(self._reset_rate, events.NewMessage(
            incoming=True, pattern=r'^/resetrate\b'))
        self.logger.info("队列管理插件事件处理器已移除")

    async def _queue_status(self, event):
        stats = await task_queue.get_queue_stats()
        await event.reply(
            f"📋 **队列状态**\n\n"
            f"⏳ 等待中: {stats['pending_tasks']}\n"
            f"▶️  运行中: {stats['running_tasks']}\n"
            f"⚡ 当前速率: {rate_limiter.rate_per_second:.1f} 请求/秒"
        )

    async def _reset_rate(self, event):
        rate_limiter.rate_per_second = 0.5
        rate_limiter.flood_wait_count = 0
        rate_limiter.success_count = 0
        await event.reply("✅ 速率限制器已重置为 0.5/s")


queue_plugin = QueuePlugin()
from ..core.base_plugin import plugin_registry
plugin_registry.register(queue_plugin)