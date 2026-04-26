"""帮助命令插件"""
import logging
from telethon import events

from ..core.base_plugin import BasePlugin
from ..core.clients import client_manager
from ..services.user_service import user_service
from ..services.permission_service import permission_service

logger = logging.getLogger(__name__)


class HelpPlugin(BasePlugin):
    """帮助命令插件"""
    
    def __init__(self):
        super().__init__("help")
        self.drone = client_manager.bot
    
    async def on_load(self):
        """插件加载时注册事件处理器"""
        # 重新获取bot实例（确保是最新的）
        self.drone = client_manager.bot
        
        if self.drone is None:
            logger.error("Bot客户端未初始化，无法注册事件处理器")
            return
        
        # 注册消息处理器
        self.drone.add_event_handler(self.help_command, events.NewMessage(incoming=True, pattern="/help"))
        
        logger.info(f"帮助插件事件处理器已注册")
    
    async def on_unload(self):
        """插件卸载时移除事件处理器"""
        # 移除事件处理器
        self.drone.remove_event_handler(self.help_command, events.NewMessage(incoming=True, pattern="/help"))
        
        logger.info("帮助插件事件处理器已移除")
    
    async def help_command(self, event):
        """处理 /help 命令"""
        from ..config import settings
        from ..services.tier_service import tier_service
        
        user_id = event.sender_id
        
        logger.info(f"收到 /help 命令，用户ID: {user_id}")
        
        # 只允许授权用户使用
        if not await permission_service.require_authorized(user_id):
            logger.warning(f"未授权用户尝试使用帮助命令: {user_id}")
            await event.reply("❌ 您没有权限使用此机器人")
            return
        
        # 检查用户是否被封禁
        if await user_service.is_user_banned(user_id):
            await event.reply("您已被封禁，无法使用此机器人。")
            return
        
        # 检查用户等级
        is_admin = tier_service.is_super_admin(user_id)
        is_premium = await tier_service.is_premium_user(user_id)
        
        if is_admin:
            user_level = "👑 **超级管理员**"
            user_perms = "• 无限制转发\n• 所有管理功能"
        elif is_premium:
            user_level = "⭐ **Premium用户**"
            user_perms = "• 批量限额更高"
        else:
            user_level = "📌 **普通用户**"
            user_perms = "• 基础转发功能"
        
        help_text = f"""🤖 **TG-Content-Bot-Pro 使用帮助**

📊 **您的账户**
{user_level}
{user_perms}

📋 **核心功能**
• 发送消息链接即可克隆内容
• 支持公开/私有频道
• 批量转发消息

🛠️ **命令列表**

**📌 用户命令**
`/start` - 🚀 开始使用
`/help` - 📖 显示帮助
`/plan` - 👑 查看账户和配额
`/batch` - 📦 批量保存消息
`/cancel` - ❌ 取消任务
`/mysession` - 🔐 查看我的SESSION

**👑 管理员命令**
`/authorize <user_id>` - 🔓 添加授权用户
`/unauthorize <user_id>` - 🔒 移除授权用户
`/authorized` - 📋 查看授权列表

`/upgrade <user_id>` - ⬆️ 升级为Premium
`/downgrade <user_id>` - ⬇️ 降级为普通用户

`/history` - 📜 查看转发历史
`/clearhistory` - 🗑️ 清除转发历史
`/queue` - 📋 查看队列状态

`/sessions` - 📋 查看所有SESSION
`/addsession` - ➕ 添加SESSION
`/generatesession` - 🔐 在线生成SESSION
`/delsession <me|user_id>` - 🗑️ 删除SESSION

⚡ **使用提示**
1. 发送消息链接即可克隆公开内容
2. 私有频道需先发送邀请链接

有问题请联系: @tgxxtq
"""
        
        await event.reply(help_text)
        logger.info(f"帮助信息已发送给用户 {user_id}")


# 创建插件实例并注册
help_plugin = HelpPlugin()

# 注册到插件注册表
from ..core.base_plugin import plugin_registry
plugin_registry.register(help_plugin)