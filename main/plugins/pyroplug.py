"""Pyrogram插件"""
import asyncio
import time
import os
from typing import Optional, Any

from ..core.base_plugin import BasePlugin
from ..core.clients import client_manager
from ..config import settings
from ..services.download_service import download_service
from ..services.traffic_service import traffic_service
from ..utils.media_utils import screenshot

from pyrogram import Client, filters
from pyrogram.errors import ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid, PeerIdInvalid
from pyrogram.enums import MessageMediaType
from ethon.pyfunc import video_metadata
from ethon.telefunc import fast_upload
from telethon.tl.types import DocumentAttributeVideo
from telethon import events

class PyroplugPlugin(BasePlugin):
    """Pyrogram插件"""
    
    def __init__(self):
        super().__init__("pyroplug")
    
    async def on_load(self):
        """插件加载时注册事件处理器"""
        # 这个插件主要提供工具函数，不需要注册事件处理器
        self.logger.info("Pyrogram插件已加载")
    
    async def on_unload(self):
        """插件卸载时调用"""
        # 这个插件主要提供工具函数，不需要特殊清理
        self.logger.info("Pyrogram插件已卸载")
    
    def thumbnail(self, sender: int) -> Optional[str]:
        """获取用户缩略图"""
        if os.path.exists(f'{sender}.jpg'):
            return f'{sender}.jpg'
        else:
            return None

# 创建插件实例并注册
pyroplug_plugin = PyroplugPlugin()

# 注册到插件注册表
from ..core.base_plugin import plugin_registry
plugin_registry.register(pyroplug_plugin)
