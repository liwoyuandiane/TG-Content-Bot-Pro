"""用户计划/等级管理插件"""
import logging

from ..core.base_plugin import BasePlugin
from ..core.clients import client_manager
from ..config import settings
from ..services.tier_service import tier_service
from ..services.user_service import user_service

from telethon import events, Button

logger = logging.getLogger(__name__)


class PlanPlugin(BasePlugin):
    """用户计划管理插件"""
    
    def __init__(self):
        super().__init__("plan")
    
    async def on_load(self):
        """插件加载时注册事件处理器"""
        client_manager.bot.add_event_handler(
            self._plan_command,
            events.NewMessage(incoming=True, pattern=r'^/plan\b')
        )
        client_manager.bot.add_event_handler(
            self._upgrade_command,
            events.NewMessage(incoming=True, pattern=r'^/upgrade\b')
        )
        client_manager.bot.add_event_handler(
            self._downgrade_command,
            events.NewMessage(incoming=True, pattern=r'^/downgrade\b')
        )
        
        self.logger.info("用户计划管理插件事件处理器已注册")
    
    async def on_unload(self):
        """插件卸载时移除事件处理器"""
        client_manager.bot.remove_event_handler(
            self._plan_command,
            events.NewMessage(incoming=True, pattern=r'^/plan\b')
        )
        client_manager.bot.remove_event_handler(
            self._upgrade_command,
            events.NewMessage(incoming=True, pattern=r'^/upgrade\b')
        )
        client_manager.bot.remove_event_handler(
            self._downgrade_command,
            events.NewMessage(incoming=True, pattern=r'^/downgrade\b')
        )
        
        self.logger.info("用户计划管理插件事件处理器已移除")
    
    async def _plan_command(self, event):
        """处理 /plan 命令 - 查看当前用户等级和配额"""
        user_id = event.sender_id
        
        # 检查用户是否授权
        if not await user_service.is_user_authorized(user_id):
            return
        
        # 获取用户信息
        is_premium = await tier_service.is_premium_user(user_id)
        is_admin = tier_service.is_super_admin(user_id)
        batch_limit = await tier_service.get_batch_limit(user_id)
        
        if is_admin:
            tier_name = "超级管理员"
            tier_desc = "所有权限，无限制"
        elif is_premium:
            tier_name = "Premium"
            tier_desc = "批量限额更高"
        else:
            tier_name = "普通用户"
            tier_desc = f"批量限额 {settings.FREEMIUM_LIMIT} 条/次"
        
        # 获取流量信息
        stats = await user_service.get_user_stats(user_id)
        total_forwards = stats.get('total_forwards', 0) if stats else 0
        
        text = f"""
**您的账户信息**

🏷️ **用户ID**: `{user_id}`
👑 **等级**: {tier_name}
📊 **状态**: {tier_desc}
📊 **当前批量限额**: {batch_limit} 条/次

**转发统计**
• 总转发数: {total_forwards}

**配额说明**
• 普通用户: {settings.FREEMIUM_LIMIT} 条/次
• Premium用户: {settings.PREMIUM_LIMIT} 条/次
• 超级管理员: 无限制

**联系管理员升级Premium**
"""
        
        await event.reply(text)
    
    async def _upgrade_command(self, event):
        """处理 /upgrade 命令 - 提升用户为Premium（仅管理员）"""
        # 检查是否是管理员
        auth_users = settings.get_auth_users()
        if event.sender_id not in auth_users:
            await event.reply("❌ 此命令仅管理员可用")
            return
        
        # 解析命令参数 - 获取目标用户ID
        args = event.text.split()[1:] if len(event.text.split()) > 1 else []
        
        if not args:
            await event.reply(
                "⬆️ **升级用户为Premium**\n\n"
                "用法: `/upgrade <user_id>`\n\n"
                "示例:\n"
                "  `/upgrade 1234567890`\n\n"
                "用户ID可通过 `/plan` 命令查看"
            )
            return
        
        try:
            target_user_id = int(args[0])
        except ValueError:
            await event.reply("❌ 无效的用户ID")
            return
        
        # 检查目标用户是否存在
        target_user = await user_service.get_user(target_user_id)
        if not target_user:
            await event.reply(f"❌ 用户 {target_user_id} 不存在")
            return
        
        # 检查用户是否已经是Premium
        if await tier_service.is_premium_user(target_user_id):
            await event.reply(f"用户 {target_user_id} 已经是Premium了")
            return
        
        # 执行升级
        success = await tier_service.upgrade_user(target_user_id)
        
        if success:
            username = target_user.get('username', '')
            name = f"@{username}" if username else f"用户{target_user_id}"
            await event.reply(f"✅ {name} 已升级为Premium")
            logger.info(f"用户 {target_user_id} 被 {event.sender_id} 升级为Premium")
        else:
            await event.reply("❌ 升级失败")
    
    async def _downgrade_command(self, event):
        """处理 /downgrade 命令 - 降级用户为普通用户（仅管理员）"""
        # 检查是否是管理员
        auth_users = settings.get_auth_users()
        if event.sender_id not in auth_users:
            await event.reply("❌ 此命令仅管理员可用")
            return
        
        # 解析命令参数 - 获取目标用户ID
        args = event.text.split()[1:] if len(event.text.split()) > 1 else []
        
        if not args:
            await event.reply(
                "⬇️ **降级用户为普通用户**\n\n"
                "用法: `/downgrade <user_id>`\n\n"
                "示例:\n"
                "  `/downgrade 1234567890`\n\n"
                "用户ID可通过 `/plan` 命令查看"
            )
            return
        
        try:
            target_user_id = int(args[0])
        except ValueError:
            await event.reply("❌ 无效的用户ID")
            return
        
        # 检查目标用户是否存在
        target_user = await user_service.get_user(target_user_id)
        if not target_user:
            await event.reply(f"❌ 用户 {target_user_id} 不存在")
            return
        
        # 检查用户是否是Premium
        if not await tier_service.is_premium_user(target_user_id):
            await event.reply(f"用户 {target_user_id} 不是Premium用户")
            return
        
        # 执行降级
        success = await tier_service.downgrade_user(target_user_id)
        
        if success:
            username = target_user.get('username', '')
            name = f"@{username}" if username else f"用户{target_user_id}"
            await event.reply(f"✅ {name} 已降级为普通用户")
            logger.info(f"用户 {target_user_id} 被 {event.sender_id} 降级为普通用户")
        else:
            await event.reply("❌ 降级失败")


# 创建插件实例并注册
plan_plugin = PlanPlugin()

# 注册到插件注册表
from ..core.base_plugin import plugin_registry
plugin_registry.register(plan_plugin)
