#!/usr/bin/env python3
"""本地功能测试脚本 - 不连接Telegram"""

import os
import sys
import asyncio
import logging

# 设置日志级别
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)

logger = logging.getLogger(__name__)

# 添加项目路径
project_path = '/data/SaveRestrictedContentBot'
if project_path not in sys.path:
    sys.path.insert(0, project_path)

# 手动加载环境变量
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
    else:
        logger.warning(f"环境文件不存在: {env_path}")
except Exception as e:
    logger.error(f"加载环境变量时出错: {e}")

async def test_core_functionality():
    """测试核心功能（不连接Telegram）"""
    try:
        logger.info("开始测试核心功能...")
        
        # 测试配置加载
        from main.config import settings
        logger.info("✅ 配置加载成功")
        logger.info(f"  API_ID: {settings.API_ID}")
        logger.info(f"  AUTH: {settings.AUTH}")
        
        # 测试数据库连接
        from main.core.database import db_manager
        logger.info("✅ 数据库连接成功")
        collections = db_manager.db.list_collection_names()
        logger.info(f"  数据库集合: {collections}")
        
        # 测试会话服务
        from main.services.session_service import session_service
        logger.info("✅ 会话服务初始化成功")
        
        # 测试插件管理器
        from main.core.plugin_manager import plugin_manager
        logger.info("✅ 插件管理器初始化成功")
        
        # 测试客户端管理器初始化（不启动客户端）
        from main.core.clients import ClientManager
        client_manager = ClientManager()
        logger.info("✅ 客户端管理器初始化成功")
        
        # 检查代理配置
        proxy_config = client_manager.proxy_config
        if proxy_config:
            logger.info("✅ 代理配置加载成功")
            logger.info(f"  方案: {proxy_config['scheme']}")
            logger.info(f"  主机: {proxy_config['hostname']}")
            logger.info(f"  端口: {proxy_config['port']}")
        else:
            logger.info("ℹ️ 未配置代理")
        
        logger.info("✅ 核心功能测试完成")
        return True
        
    except Exception as e:
        logger.error(f"核心功能测试失败: {e}")
        return False

if __name__ == "__main__":
    logger.info("开始运行本地功能测试...")
    
    try:
        result = asyncio.run(test_core_functionality())
        if result:
            logger.info("✅ 本地功能测试成功")
            sys.exit(0)
        else:
            logger.error("❌ 本地功能测试失败")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在退出...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"运行测试时出错: {e}")
        sys.exit(1)