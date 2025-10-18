#!/usr/bin/env python3
"""测试代理功能实现"""

import os
import sys
import asyncio
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)

logger = logging.getLogger(__name__)

def load_environment_variables():
    """手动加载环境变量"""
    try:
        from decouple import Config, RepositoryEnv
        env_path = os.path.join(os.getcwd(), '.env')
        if os.path.exists(env_path):
            logger.info(f"加载环境文件: {env_path}")
            env_config = Config(RepositoryEnv(env_path))
            
            # 加载关键环境变量
            env_vars = [
                'API_ID', 'API_HASH', 'BOT_TOKEN', 'AUTH', 'MONGO_DB',
                'FORCESUB', 'SESSION', 'TELEGRAM_PROXY_SCHEME', 
                'TELEGRAM_PROXY_HOST', 'TELEGRAM_PROXY_PORT',
                'ENCRYPTION_KEY'
            ]
            
            for key in env_vars:
                try:
                    value = env_config(key)
                    os.environ[key] = str(value)
                    logger.info(f"设置环境变量 {key}")
                except Exception:
                    pass  # 变量不存在，跳过
            return True
        else:
            logger.warning(f"环境文件不存在: {env_path}")
            return False
    except Exception as e:
        logger.error(f"加载环境变量时出错: {e}")
        return False

async def test_proxy_functionality():
    """测试代理功能"""
    try:
        # 添加项目路径
        project_path = '/data/SaveRestrictedContentBot'
        if project_path not in sys.path:
            sys.path.insert(0, project_path)
        
        logger.info("开始测试代理功能...")
        
        # 1. 测试配置加载
        logger.info("1. 测试配置加载...")
        from main.config import settings
        logger.info(f"   ✅ API_ID: {settings.API_ID}")
        logger.info(f"   ✅ AUTH: {settings.AUTH}")
        
        # 2. 测试代理配置
        logger.info("2. 测试代理配置...")
        from main.core.clients import ClientManager
        client_manager = ClientManager()
        proxy_config = client_manager.proxy_config
        if proxy_config:
            logger.info(f"   ✅ 代理配置加载成功: {proxy_config['scheme']}://{proxy_config['hostname']}:{proxy_config['port']}")
        else:
            logger.info("   ℹ️  未配置代理")
            
        # 3. 测试Telethon代理配置
        telethon_proxy = client_manager._get_telethon_proxy()
        if telethon_proxy:
            logger.info(f"   ✅ Telethon代理配置: {telethon_proxy}")
        else:
            logger.info("   ℹ️  Telethon未配置代理")
            
        # 4. 测试Pyrogram代理配置
        pyrogram_proxy = client_manager._get_pyrogram_proxy()
        if pyrogram_proxy:
            logger.info(f"   ✅ Pyrogram代理配置: {pyrogram_proxy}")
        else:
            logger.info("   ℹ️  Pyrogram未配置代理")
        
        # 5. 测试客户端初始化（不启动连接）
        logger.info("3. 测试客户端初始化...")
        client_manager._init_telethon_bot()
        client_manager._init_pyrogram_bot()
        logger.info("   ✅ 客户端初始化成功")
        
        logger.info("🎉 代理功能测试通过！")
        logger.info("💡 代理配置正确，客户端初始化正常")
        
        return True
        
    except Exception as e:
        logger.error(f"代理功能测试失败: {e}")
        return False

async def main():
    """主函数"""
    logger.info("开始代理功能测试...")
    
    # 加载环境变量
    if not load_environment_variables():
        logger.warning("环境变量加载失败")
    
    # 运行代理功能测试
    success = await test_proxy_functionality()
    
    if success:
        logger.info("✅ 代理功能测试成功完成")
        logger.info("💡 代理配置已准备好")
    else:
        logger.error("❌ 代理功能测试失败")
    
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)