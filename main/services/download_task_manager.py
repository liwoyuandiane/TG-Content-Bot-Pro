"""下载任务管理器"""
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from ..core.task_queue import ImprovedTaskQueue, TaskInfo, TaskStatus
from ..services.download_service import download_service
from ..core.clients import client_manager
from ..config import settings

logger = logging.getLogger(__name__)


class DownloadTaskManager:
    """下载任务管理器"""
    
    def __init__(self):
        self.task_queue = ImprovedTaskQueue(max_workers=settings.MAX_WORKERS)
        self.download_svc = download_service
        self.clients = client_manager
    
    async def start(self):
        """启动下载任务管理器"""
        await self.task_queue.start()
        logger.info("下载任务管理器已启动")
    
    async def stop(self):
        """停止下载任务管理器"""
        await self.task_queue.stop()
        logger.info("下载任务管理器已停止")
    
    def add_download_task(self, sender: int, msg_link: str, offset: int = 0, priority: int = 0) -> str:
        """添加下载任务"""
        task_name = f"下载_{msg_link.split('/')[-1]}_{offset}"
        
        # 创建任务信息
        task_id = self.task_queue.add_task(
            name=task_name,
            task_func=self._execute_download_task,
            sender=sender,
            msg_link=msg_link,
            offset=offset,
            priority=priority
        )
        
        logger.info(f"已添加下载任务: {task_name} ({task_id})")
        return task_id
    
    async def _execute_download_task(self, sender: int, msg_link: str, offset: int) -> bool:
        """执行下载任务"""
        try:
            logger.info(f"开始执行下载任务: {msg_link} (偏移: {offset})")
            
            # 执行下载
            result = await self.download_svc.download_message(
                userbot=self.clients.userbot,
                client=self.clients.pyrogram_bot,
                telethon_bot=self.clients.bot,
                sender=sender,
                edit_id=0,  # 这里需要更好的处理方式
                msg_link=msg_link,
                offset=offset
            )
            
            logger.info(f"下载任务完成: {msg_link} (偏移: {offset}) - 结果: {result}")
            return result
            
        except Exception as e:
            logger.error(f"下载任务执行失败: {msg_link} (偏移: {offset}) - 错误: {e}", exc_info=True)
            raise
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        return await self.task_queue.get_task_status(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        return await self.task_queue.cancel_task(task_id)
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        return await self.task_queue.get_queue_stats()
    
    async def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """等待任务完成"""
        return await self.task_queue.wait_for_task(task_id, timeout)
    
    async def create_batch_task(self, sender: int, start_link: str, count: int) -> str:
        """创建批量下载任务"""
        batch_task_id = f"batch_{int(datetime.now().timestamp())}"
        
        logger.info(f"开始批量下载任务: {batch_task_id} - 从 {start_link} 下载 {count} 个消息")
        
        # 添加多个下载任务
        task_ids = []
        for i in range(count):
            task_id = self.add_download_task(
                sender=sender,
                msg_link=start_link,
                offset=i,
                priority=1
            )
            task_ids.append(task_id)
        
        logger.info(f"批量下载任务 {batch_task_id} 已添加 {len(task_ids)} 个子任务")
        return batch_task_id
    
    async def update_batch_progress(self, task_id: str, completed: int) -> None:
        """更新批量任务进度"""
        logger.debug(f"批量任务 {task_id} 进度更新: {completed}")
    
    async def complete_batch_task(self, task_id: str) -> None:
        """完成批量任务"""
        logger.info(f"批量任务 {task_id} 已完成")
    
    async def cancel_batch_task(self, task_id: str) -> None:
        """取消批量任务"""
        logger.info(f"批量任务 {task_id} 已取消")
    
    async def process_batch_download(self, sender: int, start_link: str, count: int) -> str:
        """处理批量下载任务（别名方法，保持向后兼容）"""
        return await self.create_batch_task(sender, start_link, count)


# 全局下载任务管理器实例
download_task_manager = DownloadTaskManager()