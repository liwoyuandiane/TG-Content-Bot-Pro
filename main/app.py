"""应用主入口"""
import sys
import logging
import asyncio
import glob
from pathlib import Path
from pyrogram.types import BotCommand

from .core.clients import client_manager
from .core.database import db_manager
from .core.plugin_manager import plugin_manager
from .utils.logging_config import setup_logging, get_logger
from .config import settings

# 设置日志
setup_logging()
logger = get_logger(__name__)


async def setup_commands():
    """设置机器人命令"""
    commands = [
        BotCommand("start", "🚀 开始使用机器人"),
        BotCommand("batch", "📦 批量保存消息（仅所有者）"),
        BotCommand("cancel", "❌ 取消批量任务（仅所有者）"),
        BotCommand("stats", "📊 查看统计信息（仅所有者）"),
        BotCommand("history", "📜 查看下载历史（仅所有者）"),
        BotCommand("queue", "📋 查看队列状态（仅所有者）"),
        BotCommand("traffic", "📊 查看流量统计"),
        BotCommand("totaltraffic", "🌐 查看总流量（仅所有者）"),
        BotCommand("setlimit", "⚙️ 设置流量限制（仅所有者）"),
        BotCommand("resettraffic", "🔄 重置流量统计（仅所有者）"),
        BotCommand("addsession", "➕ 添加SESSION（仅所有者）"),
        BotCommand("generatesession", "🔐 在线生成SESSION（仅所有者）"),
        BotCommand("cancelsession", "🚫 取消SESSION生成（仅所有者）"),
        BotCommand("delsession", "➖ 删除SESSION（仅所有者）"),
        BotCommand("sessions", "📋 查看所有SESSION（仅所有者）"),
        BotCommand("mysession", "🔐 查看我的SESSION")
    ]
    
    try:
        await client_manager.pyrogram_bot.set_bot_commands(commands)
        logger.info("机器人命令已自动设置完成！")
    except Exception as e:
        logger.error(f"设置命令时出错: {e}", exc_info=True)


async def load_all_plugins():
    """加载所有插件"""
    try:
        from .core.base_plugin import plugin_registry
        
        results = plugin_manager.load_all_plugins()
        loaded_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        logger.info(f"插件加载完成: {loaded_count}/{total_count} 个插件加载成功")
        
        # 记录加载失败的插件
        failed_plugins = [name for name, success in results.items() if not success]
        if failed_plugins:
            logger.warning(f"以下插件加载失败: {', '.join(failed_plugins)}")
        
        # 调用所有插件的on_load()方法来注册事件处理器
        await plugin_registry.load_all_plugins()
        logger.info(f"插件事件处理器已注册")
    except Exception as e:
        logger.error(f"加载插件时出错: {e}", exc_info=True)


async def startup():
    """应用启动"""
    logger.info("=" * 50)
    logger.info("🤖 TG-Content-Bot-Pro 启动中...")
    logger.info("=" * 50)
    
    # 初始化客户端
    try:
        await client_manager.initialize_clients()
        logger.info(f"客户端初始化成功，bot实例: {client_manager.bot}")
    except Exception as e:
        logger.error(f"客户端初始化失败: {e}", exc_info=True)
        logger.warning("将继续启动应用，但部分功能可能不可用")
    
    # 启动任务队列
    try:
        from .services.download_task_manager import download_task_manager
        await download_task_manager.start()
        logger.info("✅ 下载任务队列已启动")
    except Exception as e:
        logger.error(f"启动任务队列失败: {e}", exc_info=True)
        logger.warning("任务队列启动失败，批量下载功能可能不可用")
    
    # 加载插件
    await load_all_plugins()
    
    # 检查事件处理器
    if client_manager.bot:
        handlers = list(client_manager.bot.list_event_handlers())
        logger.info(f"✅ Telethon注册的事件处理器数量: {len(handlers)}")
        for i, (handler, event) in enumerate(handlers):
            logger.info(f"  {i+1}. {handler.__name__}")
    else:
        logger.error("❌ Bot客户端未初始化！")
    
    # 设置机器人命令（确保客户端已启动）
    try:
        if client_manager.pyrogram_bot and client_manager.pyrogram_bot.is_connected:
            await setup_commands()
        else:
            logger.warning("Pyrogram客户端未连接，跳过命令设置")
    except Exception as e:
        logger.error(f"设置机器人命令失败: {e}", exc_info=True)
        logger.warning("机器人命令设置失败，但应用将继续运行")
    
    logger.info("✅ 部署成功！")
    logger.info("📱 TG消息提取器已启动")
    logger.info("🗄️  数据库初始化完成")
    logger.info("🤖 机器人命令已自动同步...")
    logger.info("=" * 50)


async def shutdown():
    """应用关闭"""
    logger.info("正在关闭应用...")
    
    # 停止任务队列
    try:
        from .services.download_task_manager import download_task_manager
        await download_task_manager.stop()
        logger.info("任务队列已停止")
    except Exception as e:
        logger.error(f"停止任务队列失败: {e}", exc_info=True)
    
    # 停止客户端
    await client_manager.stop_clients()
    logger.info("应用已关闭")


async def main_async():
    """异步主函数"""
    try:
        # 运行启动函数
        await startup()
        
        # 检查客户端是否已初始化
        if client_manager.bot is not None:
            logger.info("🚀 机器人开始监听消息...")
            # 运行主客户端直到断开连接
            await client_manager.bot.run_until_disconnected()
        else:
            logger.error("❌ 客户端未初始化，无法启动机器人")
            
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭...")
    except Exception as e:
        logger.error(f"应用运行时出错: {e}", exc_info=True)
    finally:
        # 确保正确关闭
        await shutdown()


def main():
    """主函数"""
    try:
        # 使用单个事件循环运行整个应用
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("收到中断信号")
    except Exception as e:
        logger.error(f"主函数出错: {e}", exc_info=True)


if __name__ == "__main__":
    main()