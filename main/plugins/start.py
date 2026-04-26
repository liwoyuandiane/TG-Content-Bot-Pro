"""启动插件"""
import logging
from telethon import events, Button

from ..core.base_plugin import BasePlugin
from ..core.clients import client_manager
from ..services.user_service import user_service
from ..utils.file_manager import file_manager

logger = logging.getLogger(__name__)


class StartPlugin(BasePlugin):
    """启动插件"""
    
    def __init__(self):
        super().__init__("start")
        self.drone = client_manager.bot
        self.auth_user = None  # 将从配置中获取
    
    async def on_load(self):
        """插件加载时注册事件处理器"""
        # 重新获取bot实例（确保是最新的）
        self.drone = client_manager.bot
        
        if self.drone is None:
            logger.error("Bot客户端未初始化，无法注册事件处理器")
            return
        
        # 注册回调查询处理器
        self.drone.add_event_handler(self.set_thumbnail, events.CallbackQuery(data=b"set"))
        self.drone.add_event_handler(self.remove_thumbnail, events.CallbackQuery(data=b"rem"))
        
        # 注册消息处理器 - 使用更精确的匹配
        self.drone.add_event_handler(self.start_command, events.NewMessage(incoming=True, pattern=r'^/start\b'))
        
        logger.info(f"启动插件事件处理器已注册，当前事件处理器数量: {len(list(self.drone.list_event_handlers()))}")
    
    async def on_unload(self):
        """插件卸载时移除事件处理器"""
        # 移除事件处理器
        self.drone.remove_event_handler(self.set_thumbnail, events.CallbackQuery(data=b"set"))
        self.drone.remove_event_handler(self.remove_thumbnail, events.CallbackQuery(data=b"rem"))
        self.drone.remove_event_handler(self.start_command, events.NewMessage(incoming=True, pattern=r'^/start\b'))
        
        logger.info("启动插件事件处理器已移除")
    
    async def start_message(self, event, text):
        """自定义启动消息"""
        await event.reply(
            text, 
            buttons=[
                [Button.inline("设置缩略图", data="set"),
                 Button.inline("删除缩略图", data="rem")],
                [Button.url("开发者", url="https://t.me/tgxxtq")]
            ]
        )
    
    async def set_thumbnail(self, event):    
        """设置用户缩略图"""
        drone = event.client                    
        await event.delete()
        
        async with drone.conversation(event.chat_id) as conv:
            try:
                xx = await conv.send_message("请回复此消息发送一张图片作为缩略图。")
                x = await conv.get_reply(timeout=60)
                
                if not x.media:
                    await xx.delete()
                    return await conv.send_message("未找到媒体文件。")
                
                mime = x.file.mime_type
                if mime and not any(ext in mime for ext in ['image/png', 'image/jpg', 'image/jpeg']):
                    await xx.delete()
                    return await conv.send_message("请发送有效的图片文件（PNG、JPG、JPEG）。")
                
                await xx.delete()
                t = await conv.send_message('处理中...')
                path = await drone.download_media(x.media)
                
                # 使用文件管理器安全处理文件
                user_thumb = f'{event.sender_id}.jpg'
                if file_manager.file_exists(user_thumb):
                    file_manager.safe_remove(user_thumb)
                
                file_manager.move_file(path, user_thumb)
                await t.edit("✅ 缩略图已保存！")
                
            except TimeoutError:
                await conv.send_message("⏱️ 操作超时，请重新尝试。")
            except Exception as e:
                logger.error(f"设置缩略图失败: {e}", exc_info=True)
                # 尝试发送错误消息，但如果失败则忽略
                try:
                    await conv.send_message(f"❌ 设置失败: {str(e)}")
                except:
                    pass
    
    async def remove_thumbnail(self, event):
        """删除用户缩略图"""
        await event.edit('处理中...')
        try:
            user_thumb = f'{event.sender_id}.jpg'
            if file_manager.safe_remove(user_thumb):
                await event.edit('已删除！')
            else:
                await event.edit("未保存缩略图。")
        except Exception as e:
            logger.error(f"删除缩略图失败: {e}", exc_info=True)
            await event.edit("删除缩略图时出错。")
    
    async def start_command(self, event):
        """处理 /start 命令"""
        from ..config import settings
        
        user_id = event.sender_id
        
        logger.info(f"收到 /start 命令，用户ID: {user_id}, 授权ID: {settings.AUTH}")
        
        # 只允许授权用户使用
        if not await user_service.is_user_authorized(user_id):
            logger.warning(f"未授权用户尝试使用机器人: {user_id}")
            return
        
        logger.info(f"授权用户 {user_id} 开始使用机器人")
        
        user = await event.get_sender()
        
        # 添加用户到数据库
        await user_service.add_user(
            user_id=user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        # 检查用户是否被封禁
        if await user_service.is_user_banned(user_id):
            await event.reply("您已被封禁，无法使用此机器人。")
            return
        
        # 获取用户统计信息
        stats = await user_service.get_user_stats(user_id)
        
        text = f"发送任意消息链接即可转发到这里。对于私密频道消息，请先发送邀请链接。\n\n"
        if stats:
            text += f"📊 您的统计:\n"
            text += f"• 总转发: {stats['total_forwards']}\n"
            text += f"• 总大小: {stats['total_size'] / (1024*1024):.2f} MB\n\n"
        text += "**支持:** @tgxxtq"
        
        logger.info(f"准备发送欢迎消息给用户 {user_id}")
        await self.start_message(event, text)
        logger.info(f"欢迎消息已发送给用户 {user_id}")


# 创建插件实例并注册
start_plugin = StartPlugin()

# 注册到插件注册表
from ..core.base_plugin import plugin_registry
plugin_registry.register(start_plugin)