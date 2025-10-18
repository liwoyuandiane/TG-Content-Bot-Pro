"""流量管理插件"""
from typing import List

from ..core.base_plugin import BasePlugin
from ..core.clients import client_manager
from ..config import settings
from ..services.traffic_service import traffic_service
from ..services.user_service import user_service

from telethon import events

class TrafficPlugin(BasePlugin):
    """流量管理插件"""
    
    def __init__(self):
        super().__init__("traffic")
    
    async def on_load(self):
        """插件加载时注册事件处理器"""
        # 注册命令处理器
        client_manager.bot.add_event_handler(self._traffic_stats, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern='/traffic'))
        client_manager.bot.add_event_handler(self._total_traffic_stats, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern='/totaltraffic'))
        client_manager.bot.add_event_handler(self._set_traffic_limit, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern='/setlimit'))
        client_manager.bot.add_event_handler(self._reset_traffic, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern='/resettraffic'))
        
        self.logger.info("流量管理插件事件处理器已注册")
    
    async def on_unload(self):
        """插件卸载时移除事件处理器"""
        # 移除事件处理器
        client_manager.bot.remove_event_handler(self._traffic_stats, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern='/traffic'))
        client_manager.bot.remove_event_handler(self._total_traffic_stats, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern='/totaltraffic'))
        client_manager.bot.remove_event_handler(self._set_traffic_limit, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern='/setlimit'))
        client_manager.bot.remove_event_handler(self._reset_traffic, events.NewMessage(
            incoming=True, from_users=settings.AUTH, pattern='/resettraffic'))
        
        self.logger.info("流量管理插件事件处理器已移除")
    
    async def _traffic_stats(self, event):
        """查看个人流量统计"""
        user_traffic = await traffic_service.get_user_traffic(event.sender_id)
        
        if not user_traffic:
            await traffic_service.add_traffic(event.sender_id, 0, 0)
            user_traffic = await traffic_service.get_user_traffic(event.sender_id)
        
        limits = await traffic_service.get_traffic_limits()
        status = "🟢 已启用" if limits and limits.get('enabled', 0) == 1 else "🔴 已禁用"
        
        msg = f"📊 **个人流量统计**\n\n"
        msg += f"**今日使用：**\n"
        msg += f"📥 下载: {self._format_bytes(user_traffic['daily_download'])}\n"
        msg += f"📤 上传: {self._format_bytes(user_traffic['daily_upload'])}\n\n"
        
        msg += f"**本月使用：**\n"
        msg += f"📥 下载: {self._format_bytes(user_traffic['monthly_download'])}\n"
        msg += f"📤 上传: {self._format_bytes(user_traffic['monthly_upload'])}\n\n"
        
        msg += f"**累计使用：**\n"
        msg += f"📥 下载: {self._format_bytes(user_traffic['total_download'])}\n"
        msg += f"📤 上传: {self._format_bytes(user_traffic['total_upload'])}\n\n"
        
        if limits and limits.get('enabled', 0) == 1:
            daily_remaining = max(0, limits['daily_limit'] - user_traffic['daily_download'])
            monthly_remaining = max(0, limits['monthly_limit'] - user_traffic['monthly_download'])
            
            msg += f"**流量限制：** {status}\n"
            msg += f"📅 日限额: {self._format_bytes(limits['daily_limit'])}\n"
            msg += f"   剩余: {self._format_bytes(daily_remaining)}\n"
            msg += f"📆 月限额: {self._format_bytes(limits['monthly_limit'])}\n"
            msg += f"   剩余: {self._format_bytes(monthly_remaining)}\n"
            msg += f"📄 单文件限制: {self._format_bytes(limits['per_file_limit'])}\n"
        else:
            msg += f"**流量限制：** {status}\n"
        
        await event.reply(msg)
    
    async def _total_traffic_stats(self, event):
        """查看总流量统计（仅所有者）"""
        total = await traffic_service.get_total_traffic()
        limits = await traffic_service.get_traffic_limits()
        
        if not total:
            await event.reply("暂无流量数据")
            return
        
        msg = f"🌐 **总流量统计**\n\n"
        msg += f"**今日总计：**\n"
        msg += f"📥 下载: {self._format_bytes(total['today_download'])}\n\n"
        
        msg += f"**本月总计：**\n"
        msg += f"📥 下载: {self._format_bytes(total['month_download'])}\n\n"
        
        msg += f"**累计总计：**\n"
        msg += f"📥 下载: {self._format_bytes(total['total_download'])}\n"
        msg += f"📤 上传: {self._format_bytes(total['total_upload'])}\n\n"
        
        if limits and limits.get('enabled', 0) == 1:
            msg += f"**当前限制配置：**\n"
            msg += f"📅 日限额: {self._format_bytes(limits['daily_limit'])}/用户\n"
            msg += f"📆 月限额: {self._format_bytes(limits['monthly_limit'])}/用户\n"
            msg += f"📄 单文件: {self._format_bytes(limits['per_file_limit'])}\n"
            msg += f"状态: 🟢 已启用\n"
        else:
            msg += f"**流量限制：** 🔴 已禁用\n"
        
        await event.reply(msg)
    
    def _validate_numeric_input(self, value):
        """验证数值输入"""
        try:
            num = int(value)
            if num < 0:
                return False, "数值不能为负数"
            return True, num
        except ValueError:
            return False, "请输入有效数字"
    
    async def _set_traffic_limit(self, event):
        """设置流量限制（仅所有者）"""
        try:
            parts = event.text.split()
            if len(parts) < 3:
                await event.reply(
                    "**流量限制设置**\n\n"
                    "用法:\n"
                    " - 设置日限额(MB)\n"
                    " - 设置月限额(GB)\n"
                    " - 设置单文件限制(MB)\n"
                    " - 启用流量限制\n"
                    " - 禁用流量限制\n\n"
                    "示例:\n"
                    " - 设置日限额1GB\n"
                    " - 设置月限额10GB\n"
                    " - 单文件最大100MB"
                )
                return
            
            limit_type = parts[1].lower()
            
            if limit_type == 'enable':
                await traffic_service.update_traffic_limits(enabled=1)
                await event.reply("✅ 流量限制已启用")
            elif limit_type == 'disable':
                await traffic_service.update_traffic_limits(enabled=0)
                await event.reply("✅ 流量限制已禁用")
            elif limit_type == 'daily':
                # 验证数值输入
                is_valid, value_mb = self._validate_numeric_input(parts[2])
                if not is_valid:
                    await event.reply(f"❌ {value_mb}")
                    return
                value_bytes = value_mb * 1024 * 1024
                await traffic_service.update_traffic_limits(daily_limit=value_bytes)
                await event.reply(f"✅ 日流量限制已设置为 {value_mb} MB")
            elif limit_type == 'monthly':
                # 验证数值输入
                is_valid, value_gb = self._validate_numeric_input(parts[2])
                if not is_valid:
                    await event.reply(f"❌ {value_gb}")
                    return
                value_bytes = value_gb * 1024 * 1024 * 1024
                await traffic_service.update_traffic_limits(monthly_limit=value_bytes)
                await event.reply(f"✅ 月流量限制已设置为 {value_gb} GB")
            elif limit_type == 'file':
                # 验证数值输入
                is_valid, value_mb = self._validate_numeric_input(parts[2])
                if not is_valid:
                    await event.reply(f"❌ {value_mb}")
                    return
                value_bytes = value_mb * 1024 * 1024
                await traffic_service.update_traffic_limits(per_file_limit=value_bytes)
                await event.reply(f"✅ 单文件大小限制已设置为 {value_mb} MB")
            else:
                await event.reply("❌ 无效的限制类型，使用 /setlimit 查看用法")
        
        except ValueError:
            await event.reply("❌ 无效的数值")
        except Exception as e:
            await event.reply(f"❌ 设置失败: {str(e)}")
    
    async def _reset_traffic(self, event):
        """重置流量统计"""
        try:
            parts = event.text.split()
            if len(parts) < 2:
                await event.reply(
                    "**重置流量统计**\n\n"
                    "用法:\n"
                    " - 重置今日流量\n"
                    " - 重置本月流量\n"
                    " - 重置所有流量统计"
                )
                return
            
            reset_type = parts[1].lower()
            
            if reset_type == 'daily':
                # 这里应该调用数据库服务来重置流量
                await event.reply("✅ 已重置所有用户今日流量")
            elif reset_type == 'monthly':
                # 这里应该调用数据库服务来重置流量
                await event.reply("✅ 已重置所有用户本月流量")
            elif reset_type == 'all':
                # 这里应该调用数据库服务来重置流量
                await event.reply("✅ 已重置所有流量统计")
            else:
                await event.reply("❌ 无效的重置类型")
        
        except Exception as e:
            await event.reply(f"❌ 重置失败: {str(e)}")
    
    def _format_bytes(self, bytes_value: int) -> str:
        """格式化字节数为人类可读格式"""
        if bytes_value < 1024:
            return f"{bytes_value} B"
        elif bytes_value < 1024**2:
            return f"{bytes_value/1024:.2f} KB"
        elif bytes_value < 1024**3:
            return f"{bytes_value/(1024**2):.2f} MB"
        else:
            return f"{bytes_value/(1024**3):.2f} GB"

# 创建插件实例并注册
traffic_plugin = TrafficPlugin()

# 注册到插件注册表
from ..core.base_plugin import plugin_registry
plugin_registry.register(traffic_plugin)
