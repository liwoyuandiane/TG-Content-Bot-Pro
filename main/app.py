"""应用主入口"""
import sys
import logging
import asyncio
import os
import threading
import atexit
import fcntl
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from pyrogram.types import BotCommand

from .core.clients import client_manager
from .core.database import db_manager
# plugin_manager 已移除
from .utils.logging_config import setup_logging, get_logger
from .config import settings

# 设置日志
setup_logging()
logger = get_logger(__name__)

# 全局抑制 Pyrogram 内部错误
asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

# 单实例锁文件
LOCK_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".app.lock")
lock_file = None

# 健康检查服务器实例
_health_server = None
_health_thread = None


def check_and_cleanup_session():
    """检查 API_ID 是否变化，如果变化则删除 session 文件"""
    session_dir = os.environ.get("SESSION_DIR", "/app/sessions")
    api_id_file = os.path.join(session_dir, ".api_id")
    current_api_id = str(settings.API_ID)
    
    # 如果目录不存在，创建它
    os.makedirs(session_dir, exist_ok=True)
    
    # 检查之前记录的 API_ID
    if os.path.exists(api_id_file):
        with open(api_id_file, 'r') as f:
            saved_api_id = f.read().strip()
        
        if saved_api_id != current_api_id:
            logger.warning(f"检测到 API_ID 变化: {saved_api_id} -> {current_api_id}")
            logger.warning("正在清理旧的 session 文件...")
            
            # 删除所有 session 文件
            for file in os.listdir(session_dir):
                if file.endswith('.session'):
                    file_path = os.path.join(session_dir, file)
                    os.remove(file_path)
                    logger.info(f"已删除: {file_path}")
    
    # 保存当前 API_ID
    with open(api_id_file, 'w') as f:
        f.write(current_api_id)


# 启动时检查 session
check_and_cleanup_session()


# 健康检查处理器
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>TG Content Bot Pro</h1><p>Status: Running</p><p><a href="/health">Health Check</a></p></body></html>')
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        # 重写日志方法，避免打印到控制台
        pass


def acquire_lock():
    """获取单实例锁"""
    global lock_file
    try:
        # 检查锁文件是否已存在
        if os.path.exists(LOCK_FILE_PATH):
            # 尝试读取现有锁文件中的PID
            try:
                with open(LOCK_FILE_PATH, 'r') as f:
                    existing_pid = f.read().strip()
                    if existing_pid:
                        # 检查该进程是否仍在运行
                        try:
                            os.kill(int(existing_pid), 0)  # 不发送信号，只检查进程是否存在
                            logger.error(f"❌ 检测到另一个实例正在运行 (PID: {existing_pid})，无法启动多个实例")
                            return False
                        except (OSError, ValueError):
                            # 进程不存在，可以安全地覆盖锁文件
                            logger.warning(f"⚠️  检测到陈旧的锁文件 (PID: {existing_pid} 已不存在)，将重新创建锁")
            except Exception as e:
                logger.warning(f"⚠️  读取现有锁文件时出错: {e}，将重新创建锁")
        
        # 创建锁文件
        try:
            lock_file = open(LOCK_FILE_PATH, 'w')
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except Exception:
            if lock_file:
                lock_file.close()
            raise
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        logger.info("✅ 成功获取单实例锁")
        return True
    except IOError:
        logger.error("❌ 无法获取单实例锁，可能已有另一个实例在运行")
        if lock_file:
            lock_file.close()
            lock_file = None
        return False

def release_lock():
    """释放单实例锁"""
    global lock_file
    if lock_file:
        try:
            # 删除锁文件
            os.unlink(LOCK_FILE_PATH)
            lock_file.close()
            logger.info("🔒 单实例锁已释放")
        except Exception as e:
            logger.error(f"❌ 释放单实例锁时出错: {e}")
        finally:
            lock_file = None

def start_health_server():
    """启动健康检查HTTP服务器"""
    global _health_server, _health_thread
    try:
        port = settings.HEALTH_CHECK_PORT

        _health_server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        _health_thread = threading.Thread(target=_health_server.serve_forever, daemon=True)
        _health_thread.start()
        logger.info(f"✅ 健康检查服务器已启动，端口: {port}")
    except Exception as e:
        logger.error(f"❌ 启动健康检查服务器失败: {e}")
        raise


def stop_health_server():
    """停止健康检查HTTP服务器"""
    global _health_server
    if _health_server:
        try:
            _health_server.shutdown()
            _health_server.server_close()
            _health_server = None
            logger.info("✅ 健康检查服务器已停止")
        except Exception as e:
            logger.error(f"❌ 停止健康检查服务器失败: {e}")


def check_and_reset_database():
    """检查并重置数据库（如果DB_RESET环境变量为true）"""
    db_reset = os.environ.get('DB_RESET', '').lower() in ['true', '1', 'yes']
    
    if db_reset:
        logger.info("🔄 检测到 DB_RESET=true，开始重置数据库...")
        
        try:
            if not db_manager.is_connected():
                logger.error("❌ 数据库未连接，无法执行重置")
                return False
                
            # 删除所有集合中的数据
            collections = ["users", "message_history", "batch_tasks", "settings"]
            for collection_name in collections:
                if collection_name in db_manager.db.list_collection_names():
                    count = db_manager.db[collection_name].count_documents({})
                    db_manager.db[collection_name].delete_many({})
                    logger.info(f"  ✅ 清空集合 {collection_name} ({count} 条记录)")
            
            # 重新创建必要的索引
            logger.info("  🔄 重新创建索引...")
            db_manager._create_indexes()
            
            # 添加主用户
            auth_users = settings.get_auth_users()
            for user_id in auth_users:
                db_manager.db.users.insert_one({
                    "user_id": user_id,
                    "is_authorized": True,
                    "is_banned": False,
                    "join_date": datetime.now(),
                    "total_forwards": 0,
                    "total_size": 0,
                    "daily_upload": 0,
                    "daily_download": 0,
                    "monthly_upload": 0,
                    "monthly_download": 0,
                    "total_upload": 0,
                    "total_download": 0,
                    "last_reset_daily": datetime.now().date().isoformat(),
                    "last_reset_monthly": datetime.now().strftime("%Y-%m")
                })
                logger.info(f"  ✅ 添加主用户 {user_id}")
            
            logger.info("✅ 数据库重置完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 数据库重置过程中出错: {e}")
            return False


async def setup_commands():
    """设置机器人命令"""
    commands = [
        # 用户命令
        BotCommand("start", "🚀 开始使用"),
        BotCommand("help", "📖 显示帮助"),
        BotCommand("plan", "👑 我的账户信息"),
        BotCommand("batch", "📦 批量保存消息"),
        BotCommand("cancel", "❌ 取消当前任务"),
        
        # 管理员命令 - 用户管理
        BotCommand("authorize", "🔓 授权用户\n用法: /authorize 123456789"),
        BotCommand("unauthorize", "🔒 移除授权\n用法: /unauthorize 123456789"),
        BotCommand("authorized", "📋 授权列表"),
        
        # 管理员命令 - 等级管理
        BotCommand("upgrade", "⬆️ 升级Premium\n用法: /upgrade 123456789"),
        BotCommand("downgrade", "⬇️ 降级普通\n用法: /downgrade 123456789"),
        
        # 管理员命令 - 数据管理
        BotCommand("history", "📜 转发历史"),
        BotCommand("clearhistory", "🗑️ 清除历史"),
        
        # 管理员命令 - SESSION管理
        BotCommand("sessions", "📋 所有SESSION"),
        BotCommand("addsession", "➕ 添加SESSION\n用法: /addsession <session>"),
        BotCommand("generatesession", "🔐 生成SESSION"),
        BotCommand("delsession", "🗑️ 删除SESSION\n用法: /delsession me"),
        BotCommand("mysession", "🔐 我的SESSION"),
        
        # 管理员命令 - 队列
        BotCommand("queue", "📋 队列状态"),
    ]
    
    try:
        await client_manager.bot.set_bot_commands(commands)
        logger.info("机器人命令已自动设置完成！")
    except Exception as e:
        logger.error(f"设置命令时出错: {e}", exc_info=True)


# 不再加载插件系统


async def startup():
    """应用启动"""
    logger.info("=" * 50)
    logger.info("🤖 TG-Content-Bot-Pro 启动中...")
    logger.info("=" * 50)
    
    # 检查并重置数据库（如果需要）
    check_and_reset_database()
    
    # 配置验证（使用 config.py 中的验证）
    if not settings._validated:
        logger.warning("⚠️ 配置验证失败，应用将以降级模式启动")
        logger.warning("📡 仅启动健康检查服务，无法连接到Telegram")
        logger.warning("💡 请检查.env文件中的API_ID、API_HASH和BOT_TOKEN配置")
        
        # 降级模式：只启动健康检查服务
        return False
    
    # 初始化客户端
    try:
        await client_manager.initialize_clients()
        logger.info(f"客户端初始化成功")
    except Exception as e:
        logger.error(f"客户端初始化失败: {e}", exc_info=True)
        logger.warning("将继续启动应用，但部分功能可能不可用")
    
    # 注册 Pyrogram 消息处理器
    if client_manager.bot:
        from .handlers import register_all_handlers
        register_all_handlers(client_manager.bot)
        logger.info("✅ Pyrogram 消息处理器已注册")
    else:
        logger.error("❌ Bot客户端未初始化！")
    
    # 设置机器人命令
    try:
        if client_manager.bot and client_manager.bot.is_connected:
            await setup_commands()
        else:
            logger.warning("Pyrogram客户端未连接，跳过命令设置")
    except Exception as e:
        logger.error(f"设置机器人命令失败: {e}", exc_info=True)
    
    logger.info("✅ 部署成功！")
    logger.info("📱 TG消息提取器已启动")
    logger.info("🗄️  数据库初始化完成")
    logger.info("🤖 机器人命令已自动同步...")
    logger.info("=" * 50)


async def shutdown():
    """应用关闭"""
    logger.info("正在关闭应用...")

    # 停止客户端
    await client_manager.stop_clients()

    # 停止健康检查服务器
    stop_health_server()

    logger.info("应用已关闭")


async def main_async():
    """异步主函数"""
    try:
        # 运行启动函数
        startup_result = await startup()
        
        # 如果启动失败（配置无效），进入降级模式
        if startup_result is False:
            logger.info("📡 降级模式启动完成 - 仅健康检查服务可用")
            logger.info(f"🔗 健康检查地址: http://localhost:{settings.HEALTH_CHECK_PORT}/health")
            logger.info("💡 请配置有效的Telegram API凭证以启用完整功能")
            
            # 保持应用运行，提供健康检查服务
            try:
                while True:
                    await asyncio.sleep(60)  # 每分钟检查一次
                    logger.debug("降级模式运行中...")
            except KeyboardInterrupt:
                logger.info("收到中断信号，正在关闭...")
            return
        
        # 检查客户端是否已初始化
        if client_manager.bot is not None and hasattr(client_manager.bot, 'is_connected') and client_manager.bot.is_connected:
            logger.info("🚀 机器人开始监听消息...")
            
            # Pyrogram: 保持客户端运行
            try:
                while True:
                    await asyncio.sleep(3600)  # 每小时检查一次
            except asyncio.CancelledError:
                logger.info("收到停止信号")
        else:
            logger.warning("⚠️ 客户端未初始化或未连接，机器人将以降级模式运行...")
            logger.info(f"📡 健康检查服务器已启动，可以访问 http://localhost:{settings.HEALTH_CHECK_PORT}/health 检查服务状态")
            logger.info("⏰ 应用将保持运行，等待客户端连接...")
            
            # 保持应用运行，即使客户端未连接
            try:
                while True:
                    await asyncio.sleep(60)  # 每分钟检查一次
                    logger.debug("应用仍在运行...")
            except KeyboardInterrupt:
                logger.info("收到中断信号，正在关闭...")
            
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭...")
    except Exception as e:
        logger.error(f"应用运行时出错: {e}", exc_info=True)
    finally:
        # 确保正确关闭
        await shutdown()


def main():
    """主函数"""
    # 检查是否能获取单实例锁
    if not acquire_lock():
        logger.error("🚨 程序已在运行中，无法启动多个实例")
        logger.info("💡 如需启动新实例，请先停止当前运行的实例")
        sys.exit(1)
    
    # 注册退出处理函数，确保程序退出时释放锁和关闭服务
    atexit.register(release_lock)
    atexit.register(stop_health_server)

    # 启动健康检查服务器
    start_health_server()
    
    try:
        # 使用单个事件循环运行整个应用
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("收到中断信号")
    except Exception as e:
        logger.error(f"主函数出错: {e}", exc_info=True)
    finally:
        # 确保释放锁
        release_lock()


if __name__ == "__main__":
    main()