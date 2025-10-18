#!/usr/bin/env python3
"""机器人调试工具"""

import sys
import os
import asyncio
import logging

# 添加项目路径
project_path = os.path.dirname(os.path.abspath(__file__))
if project_path not in sys.path:
    sys.path.insert(0, project_path)

# 设置调试日志
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s/%(asctime)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

async def debug_bot():
    """调试机器人启动"""
    try:
        print("\n" + "="*60)
        print("TG-Content-Bot-Pro 调试工具")
        print("="*60 + "\n")
        
        # 1. 检查配置
        print("📋 步骤 1: 检查配置...")
        from main.config import settings
        print(f"  ✅ API_ID: {settings.API_ID}")
        print(f"  ✅ AUTH: {settings.AUTH}")
        print(f"  ✅ BOT_TOKEN: {settings.BOT_TOKEN[:20]}...")
        print(f"  ✅ MONGO_DB: 已配置")
        print(f"  ℹ️  SESSION: {'已配置' if settings.SESSION else '未配置（正常，可后续添加）'}")
        
        # 2. 检查数据库连接
        print("\n📋 步骤 2: 检查数据库连接...")
        from main.core.database import db_manager
        print("  ✅ 数据库连接成功")
        
        # 3. 检查客户端管理器
        print("\n📋 步骤 3: 初始化Telegram客户端...")
        from main.core.clients import client_manager
        
        try:
            await client_manager.initialize_clients()
            print("  ✅ 客户端初始化成功")
        except Exception as e:
            print(f"  ❌ 客户端初始化失败: {e}")
            logger.exception("详细错误信息:")
            
        # 4. 检查客户端状态
        print("\n📋 步骤 4: 检查客户端状态...")
        status = client_manager.get_client_status()
        print(f"  Telethon Bot: {'✅ 已连接' if status['telethon_bot'] else '❌ 未连接'}")
        print(f"  Pyrogram Bot: {'✅ 已连接' if status['pyrogram_bot'] else '❌ 未连接'}")
        print(f"  Userbot: {'✅ 已连接' if status['userbot'] else '❌ 未配置或未连接'}")
        print(f"  代理: {'✅ 已启用' if status['proxy_enabled'] else 'ℹ️  未启用'}")
        
        # 5. 检查插件加载
        print("\n📋 步骤 5: 检查插件加载...")
        from main.core.plugin_manager import plugin_manager
        results = plugin_manager.load_all_plugins()
        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)
        print(f"  插件加载: {success_count}/{total_count} 个成功")
        
        for name, success in results.items():
            if success:
                print(f"    ✅ {name}")
            else:
                print(f"    ❌ {name}")
        
        # 6. 检查事件处理器
        print("\n📋 步骤 6: 检查事件处理器...")
        if client_manager.bot:
            handlers = list(client_manager.bot.list_event_handlers())
            print(f"  已注册事件处理器数量: {len(handlers)}")
            if len(handlers) == 0:
                print("  ⚠️  警告: 没有注册任何事件处理器！")
            else:
                print("  ✅ 事件处理器已注册")
        else:
            print("  ❌ Telethon bot 未初始化，无法检查事件处理器")
        
        # 7. 诊断建议
        print("\n" + "="*60)
        print("诊断结果和建议:")
        print("="*60)
        
        if not status['telethon_bot']:
            print("❌ 问题: Telethon Bot 未连接")
            print("   可能原因:")
            print("   1. 网络连接问题（无法访问Telegram服务器）")
            print("   2. BOT_TOKEN 无效")
            print("   3. 代理配置错误")
            print("   解决方案:")
            print("   - 检查网络连接")
            print("   - 验证BOT_TOKEN是否正确")
            print("   - 如果在中国大陆，需要配置代理")
            
        if not status['pyrogram_bot']:
            print("\n❌ 问题: Pyrogram Bot 未连接")
            print("   可能原因:")
            print("   1. 网络连接问题")
            print("   2. API凭证无效")
            print("   解决方案:")
            print("   - 检查网络连接")
            print("   - 验证API_ID和API_HASH")
        
        if len(handlers) == 0 and client_manager.bot:
            print("\n❌ 问题: 没有注册事件处理器")
            print("   可能原因:")
            print("   1. 插件加载失败")
            print("   2. 插件未正确注册事件处理器")
            print("   解决方案:")
            print("   - 查看上面的插件加载状态")
            print("   - 检查失败的插件错误日志")
        
        if status['telethon_bot'] and status['pyrogram_bot'] and len(handlers) > 0:
            print("\n✅ 所有检查通过！机器人应该可以正常工作")
            print("   如果仍然无响应，请:")
            print("   1. 确保发送消息的用户ID与AUTH配置一致")
            print("   2. 尝试发送 /start 命令")
            print("   3. 检查机器人是否被Telegram限制")
        
        print("\n" + "="*60)
        print("调试完成")
        print("="*60 + "\n")
        
        # 清理
        await client_manager.stop_clients()
        
    except Exception as e:
        logger.exception("调试过程中出错:")
        print(f"\n❌ 调试失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(debug_bot())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  调试被用户中断")
        sys.exit(0)
