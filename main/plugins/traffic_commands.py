"""流量管理插件"""
from typing import List

from ..core.base_plugin import BasePlugin
from ..core.clients import client_manager
from ..core.database import db_manager
from ..services.traffic_service import traffic_service
from ..services.user_service import user_service
from ..services.permission_service import permission_service

from telethon import events

class TrafficPlugin(BasePlugin):
    """流量管理插件"""
    
    def __init__(self):
        super().__init__("traffic")
    
    async def on_load(self):
        """插件加载时注册事件处理器"""
        # 注册命令处理器 - 使用更简单的模式匹配，在handler内进行权限检查
        client_manager.bot.add_event_handler(self._traffic_stats, events.NewMessage(
            incoming=True, pattern='/traffic'))
        client_manager.bot.add_event_handler(self._total_traffic_stats, events.NewMessage(
            incoming=True, pattern='/totaltraffic'))
        client_manager.bot.add_event_handler(self._bot_stats, events.NewMessage(
            incoming=True, pattern='/stats'))
        client_manager.bot.add_event_handler(self._forward_history, events.NewMessage(
            incoming=True, pattern='/history'))
        client_manager.bot.add_event_handler(self._set_traffic_limit, events.NewMessage(
            incoming=True, pattern='/setlimit'))
        client_manager.bot.add_event_handler(self._reset_traffic, events.NewMessage(
            incoming=True, pattern='/resettraffic'))
        client_manager.bot.add_event_handler(self._clear_history, events.NewMessage(
            incoming=True, pattern='/clearhistory'))
        client_manager.bot.add_event_handler(self._confirm_clear_history, events.NewMessage(
            incoming=True, pattern='/clearhistory confirm'))
        
        # 注册回调处理器
        client_manager.bot.add_event_handler(self._handle_history_navigation, events.CallbackQuery())
        
        self.logger.info("流量管理插件事件处理器已注册")
    
    async def on_unload(self):
        """插件卸载时移除事件处理器"""
        # 移除事件处理器 - 不再使用from_users限制，在handler内进行权限检查
        client_manager.bot.remove_event_handler(self._traffic_stats, events.NewMessage(
            incoming=True, pattern='/traffic'))
        client_manager.bot.remove_event_handler(self._total_traffic_stats, events.NewMessage(
            incoming=True, pattern='/totaltraffic'))
        client_manager.bot.remove_event_handler(self._bot_stats, events.NewMessage(
            incoming=True, pattern='/stats'))
        client_manager.bot.remove_event_handler(self._forward_history, events.NewMessage(
            incoming=True, pattern='/history'))
        client_manager.bot.remove_event_handler(self._set_traffic_limit, events.NewMessage(
            incoming=True, pattern='/setlimit'))
        client_manager.bot.remove_event_handler(self._reset_traffic, events.NewMessage(
            incoming=True, pattern='/resettraffic'))
        client_manager.bot.remove_event_handler(self._clear_history, events.NewMessage(
            incoming=True, pattern='/clearhistory'))
        client_manager.bot.remove_event_handler(self._confirm_clear_history, events.NewMessage(
            incoming=True, pattern='/clearhistory confirm'))
        
        # 移除回调处理器
        client_manager.bot.remove_event_handler(self._handle_history_navigation, events.CallbackQuery())
        
        self.logger.info("流量管理插件事件处理器已移除")
    
    async def _traffic_stats(self, event):
        """查看个人流量统计"""
        # 权限检查：允许所有授权用户查看自己的流量统计
        if not await permission_service.require_authorized(event.sender_id):
            await event.reply("❌ 您没有权限使用此命令")
            return
        
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
        # 权限检查：只允许所有者使用
        if not await permission_service.require_owner(event.sender_id):
            await event.reply("❌ 此命令仅限所有者使用")
            return
        
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
            # 权限检查：只允许所有者使用
            if not await permission_service.require_owner(event.sender_id):
                await event.reply("❌ 此命令仅限所有者使用")
                return
            
            parts = event.text.split()
            if len(parts) < 3:
                await event.reply(
                    "**流量限制设置**\n\n"
                    "**用法:**\n"
                    "`/setlimit <类型> <值>`\n\n"
                    "**类型说明:**\n"
                    "- `daily`: 设置每日流量限制（单位：MB）\n"
                    "- `monthly`: 设置每月流量限制（单位：GB）\n"
                    "- `file`: 设置单文件大小限制（单位：MB）\n"
                    "- `enable`: 启用流量限制功能\n"
                    "- `disable`: 禁用流量限制功能\n\n"
                    "**示例（点击可直接复制）:**\n"
                    "- `/setlimit daily 1024`  （设置每日限制为1GB）\n"
                    "- `/setlimit monthly 10`  （设置每月限制为10GB）\n"
                    "- `/setlimit file 100`    （设置单文件限制为100MB）\n"
                    "- `/setlimit enable`      （启用流量限制）\n"
                    "- `/setlimit disable`     （禁用流量限制）"
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
            # 权限检查：只允许所有者使用
            if not await permission_service.require_owner(event.sender_id):
                await event.reply("❌ 此命令仅限所有者使用")
                return
            
            parts = event.text.split()
            if len(parts) < 2:
                await event.reply(
                    "**重置流量统计**\n\n"
                    "**用法:**\n"
                    "`/resettraffic <类型>`\n\n"
                    "**类型说明:**\n"
                    "`daily` - 重置所有用户的今日流量统计\n"
                    "`monthly` - 重置所有用户的本月流量统计\n"
                    "`all` - 重置所有流量统计（包括历史累计）\n\n"
                    "**示例:**\n"
                    "`/resettraffic daily`   （重置今日流量）\n"
                    "`/resettraffic monthly` （重置本月流量）\n"
                    "`/resettraffic all`     （重置所有流量统计）"
                )
                return
            
            reset_type = parts[1].lower()
            
            if reset_type == 'daily':
                from ..core.database import db_manager
                success = await db_manager.reset_daily_traffic()
                if success:
                    await event.reply("✅ 已重置所有用户今日流量")
                else:
                    await event.reply("❌ 重置今日流量失败")
            elif reset_type == 'monthly':
                from ..core.database import db_manager
                success = await db_manager.reset_monthly_traffic()
                if success:
                    await event.reply("✅ 已重置所有用户本月流量")
                else:
                    await event.reply("❌ 重置本月流量失败")
            elif reset_type == 'all':
                from ..core.database import db_manager
                success = await db_manager.reset_all_traffic()
                if success:
                    await event.reply("✅ 已重置所有流量统计")
                else:
                    await event.reply("❌ 重置所有流量统计失败")
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
    
    async def _bot_stats(self, event):
        """查看机器人统计信息（仅所有者）"""
        try:
            # 权限检查：只允许所有者使用
            if not await permission_service.require_owner(event.sender_id):
                await event.reply("❌ 此命令仅限所有者使用")
                return
            
            # 获取用户统计
            total_users = await user_service.get_all_users_count()
            
            # 获取转发统计
            total_forwards = await user_service.get_total_forwards()
            
            # 获取流量统计
            total_traffic = await traffic_service.get_total_traffic()
            
            from ..plugins.queue_commands import task_queue
            queue_stats = await task_queue.get_queue_stats()
            
            msg = "🤖 **机器人统计信息**\n\n"
            msg += f"👥 用户总数: {total_users}\n"
            msg += f"📤 总转发数: {total_forwards}\n\n"
            
            if total_traffic:
                msg += f"📊 **总流量统计**\n"
                msg += f"📥 下载: {self._format_bytes(total_traffic['total_download'])}\n"
                msg += f"📤 上传: {self._format_bytes(total_traffic['total_upload'])}\n\n"
            
            msg += f"📋 **队列状态**\n"
            msg += f"⏳ 等待中: {queue_stats['pending_tasks']}\n"
            msg += f"▶️  运行中: {queue_stats['running_tasks']}\n"
            
            await event.reply(msg)
        except Exception as e:
            await event.reply(f"❌ 获取统计信息失败: {str(e)}")
    
    async def _forward_history(self, event):
        """查看转发历史（仅所有者）"""
        try:
            # 权限检查：只允许所有者使用
            if not await permission_service.require_owner(event.sender_id):
                await event.reply("❌ 此命令仅限所有者使用")
                return
            
            # 解析页码参数
            page = 1
            if event.text.startswith('/history '):
                try:
                    page = int(event.text.split()[1])
                    if page < 1:
                        page = 1
                except (ValueError, IndexError):
                    page = 1
            
            # 每页显示的记录数
            records_per_page = 5
            
            # 从数据库获取转发历史（带分页）
            from ..core.database import db_manager
            offset = (page - 1) * records_per_page
            history = await db_manager.get_recent_forward_history(limit=records_per_page, offset=offset)
            
            # 获取总记录数以计算总页数
            # 这里简化处理，假设总记录数远大于当前页
            # 实际应用中可能需要添加获取总记录数的方法
            
            if not history:
                if page == 1:
                    await event.reply("📭 暂无转发历史")
                else:
                    await event.reply("📭 已经到达最后一页")
                return
            
            msg = f"📜 **最近转发历史** (第 {page} 页)\n\n"
            
            for record in history:
                # 安全地获取记录字段
                try:
                    # 格式化时间
                    from datetime import datetime
                    forward_date = record.get('forward_date')
                    if forward_date is None:
                        timestamp = datetime.now()
                    elif isinstance(forward_date, str):
                        timestamp = datetime.fromisoformat(forward_date.replace('Z', '+00:00'))
                    else:
                        timestamp = forward_date
                    
                    # 格式化文件大小
                    file_size = self._format_bytes(record.get('file_size', 0))
                    
                    msg += f"📤 {timestamp.strftime('%m-%d %H:%M')}\n"
                    # 显示消息链接（如果存在）
                    message_link = record.get('message_link')
                    if message_link:
                        msg += f"   链接: {message_link}\n"
                    msg += f"   文件大小: {file_size}\n"
                    # 状态和类型中文翻译
                    status_map = {
                        "success": "✅ 成功",
                        "failed": "❌ 失败",
                        "pending": "⏳ 等待中",
                        "processing": "🔄 处理中"
                    }
                    
                    media_type_map = {
                        "photo": "📸 图片",
                        "video": "🎬 视频",
                        "document": "📄 文档",
                        "audio": "🎵 音频",
                        "voice": "🎤 语音",
                        "sticker": "😀 贴纸",
                        "animation": "🎭 动画",
                        "video_note": "📺 视频消息",
                        "unknown": "❓ 未知"
                    }
                    
                    status_val = record.get('status', '未知')
                    media_type_val = record.get('media_type', '未知')
                    
                    status_cn = status_map.get(status_val, status_val)
                    media_type_cn = media_type_map.get(media_type_val, media_type_val)
                    
                    msg += f"   状态: {status_cn}\n"
                    msg += f"   类型: {media_type_cn}\n\n"
                except Exception as e:
                    logger.error(f"处理历史记录时出错: {e}")
                    msg += "   ❌ 记录处理错误\n\n"
            
            # 添加分页导航按钮
            from telethon.tl.types import KeyboardButtonCallback
            
            buttons = []
            if page > 1:
                buttons.append([KeyboardButtonCallback('⬅️ 上一页', f'history_page_{page-1}'.encode())])
            
            # 这里简化处理，总是显示下一页按钮
            # 实际应用中应该检查是否还有更多记录
            buttons.append([KeyboardButtonCallback('➡️ 下一页', f'history_page_{page+1}'.encode())])
            
            # 发送带按钮的消息
            await event.reply(msg, buttons=buttons if buttons else None)
        except Exception as e:
            import traceback
            logger.error(f"获取转发历史失败: {e}")
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            await event.reply(f"❌ 获取转发历史失败: {str(e)}")
    
    async def _handle_history_navigation(self, event):
        """处理历史记录分页导航"""
        try:
            # 权限检查：只允许所有者使用
            if not await permission_service.require_owner(event.sender_id):
                await event.answer("❌ 您没有权限使用此功能")
                return
            
            # 解析页码
            callback_data = event.data.decode()
            if callback_data.startswith('history_page_'):
                page = int(callback_data.split('_')[2])
                
                # 每页显示的记录数
                records_per_page = 5
                
                # 从数据库获取转发历史（带分页）
                from ..core.database import db_manager
                offset = (page - 1) * records_per_page
                history = await db_manager.get_recent_forward_history(limit=records_per_page, offset=offset)
                
                if not history:
                    await event.answer("📭 已经到达最后一页")
                    return
                
                msg = f"📜 **最近转发历史** (第 {page} 页)\n\n"
                
                for record in history:
                    # 安全地获取记录字段
                    try:
                        # 格式化时间
                        from datetime import datetime
                        forward_date = record.get('forward_date')
                        if forward_date is None:
                            timestamp = datetime.now()
                        elif isinstance(forward_date, str):
                            timestamp = datetime.fromisoformat(forward_date.replace('Z', '+00:00'))
                        else:
                            timestamp = forward_date
                        
                        # 格式化文件大小
                        file_size = self._format_bytes(record.get('file_size', 0))
                        
                        msg += f"📤 {timestamp.strftime('%m-%d %H:%M')}\n"
                        # 显示消息链接（如果存在）
                        message_link = record.get('message_link')
                        if message_link:
                            msg += f"   链接: {message_link}\n"
                        msg += f"   文件大小: {file_size}\n"
                        # 状态和类型中文翻译
                        status_map = {
                            "success": "✅ 成功",
                            "failed": "❌ 失败",
                            "pending": "⏳ 等待中",
                            "processing": "🔄 处理中"
                        }
                        
                        media_type_map = {
                            "photo": "📸 图片",
                            "video": "🎬 视频",
                            "document": "📄 文档",
                            "audio": "🎵 音频",
                            "voice": "🎤 语音",
                            "sticker": "😀 贴纸",
                            "animation": "🎭 动画",
                            "video_note": "📺 视频消息",
                            "unknown": "❓ 未知"
                        }
                        
                        status_val = record.get('status', '未知')
                        media_type_val = record.get('media_type', '未知')
                        
                        status_cn = status_map.get(status_val, status_val)
                        media_type_cn = media_type_map.get(media_type_val, media_type_val)
                        
                        msg += f"   状态: {status_cn}\n"
                        msg += f"   类型: {media_type_cn}\n\n"
                    except Exception as e:
                        logger.error(f"处理历史记录时出错: {e}")
                        msg += "   ❌ 记录处理错误\n\n"
                
                # 添加分页导航按钮
                from telethon.tl.types import KeyboardButtonCallback
                
                buttons = []
                if page > 1:
                    buttons.append([KeyboardButtonCallback('⬅️ 上一页', f'history_page_{page-1}'.encode())])
                
                # 这里简化处理，总是显示下一页按钮
                # 实际应用中应该检查是否还有更多记录
                buttons.append([KeyboardButtonCallback('➡️ 下一页', f'history_page_{page+1}'.encode())])
                
                # 编辑消息内容和按钮
                await event.edit(msg, buttons=buttons)
                await event.answer()
        except Exception as e:
            import traceback
            logger.error(f"导航失败: {e}")
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            await event.answer(f"❌ 导航失败: {str(e)}")
    
    async def _clear_history(self, event):
        """清除所有转发历史（仅所有者）"""
        try:
            # 权限检查：只允许所有者使用
            if not await permission_service.require_owner(event.sender_id):
                await event.reply("❌ 此命令仅限所有者使用")
                return
            
            # 确认操作
            await event.reply(
                "⚠️ **警告：此操作将永久删除所有转发历史记录！**\n\n"
                "请确认您要继续执行此操作...\n\n"
                "回复 `/clearhistory confirm` 来确认删除"
            )
        except Exception as e:
            await event.reply(f"❌ 操作失败: {str(e)}")
    
    async def _confirm_clear_history(self, event):
        """确认清除转发历史"""
        try:
            # 权限检查：只允许所有者使用
            if not await permission_service.require_owner(event.sender_id):
                await event.reply("❌ 此命令仅限所有者使用")
                return
            
            # 调用数据库服务来清除转发历史
            from ..core.database import db_manager
            success = await db_manager.clear_forward_history()
            if success:
                await event.reply("✅ 已清除所有转发历史记录")
            else:
                await event.reply("❌ 清除转发历史记录失败")
        except Exception as e:
            await event.reply(f"❌ 操作失败: {str(e)}")


# 创建插件实例并注册
traffic_plugin = TrafficPlugin()

# 注册到插件注册表
from ..core.base_plugin import plugin_registry
plugin_registry.register(traffic_plugin)