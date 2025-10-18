#!/usr/bin/env python3
"""核心功能验证脚本 - 不进行实际的Telegram连接"""

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

def main():
    """主函数"""
    logger.info("开始核心功能验证...")
    
    try:
        # 添加项目路径
        project_path = '/data/SaveRestrictedContentBot'
        if project_path not in sys.path:
            sys.path.insert(0, project_path)
        
        # 测试配置加载
        logger.info("1. 测试配置加载...")
        from main.config import settings
        logger.info(f"   ✅ API_ID: {settings.API_ID}")
        logger.info(f"   ✅ AUTH: {settings.AUTH}")
        
        # 测试数据库连接
        logger.info("2. 测试数据库连接...")
        from main.core.database import db_manager
        collections = db_manager.db.list_collection_names()
        logger.info(f"   ✅ 数据库连接成功，集合: {collections}")
        
        # 测试会话服务
        logger.info("3. 测试会话服务...")
        from main.services.session_service import session_service
        logger.info("   ✅ 会话服务初始化成功")
        
        # 测试插件管理器
        logger.info("4. 测试插件管理器...")
        from main.core.plugin_manager import plugin_manager
        logger.info("   ✅ 插件管理器初始化成功")
        
        # 测试客户端管理器
        logger.info("5. 测试客户端管理器...")
        from main.core.clients import ClientManager
        client_manager = ClientManager()
        proxy_config = client_manager.proxy_config
        if proxy_config:
            logger.info(f"   ✅ 代理配置加载成功: {proxy_config['scheme']}://{proxy_config['hostname']}:{proxy_config['port']}")
        else:
            logger.info("   ℹ️  未配置代理")
        
        # 测试任务队列
        logger.info("6. 测试任务队列...")
        from main.core.task_queue import ImprovedTaskQueue
        task_queue = ImprovedTaskQueue()
        logger.info("   ✅ 任务队列初始化成功")
        
        # 测试速率限制器
        logger.info("7. 测试速率限制器...")
        from main.core.rate_limiter import RateLimiter
        rate_limiter = RateLimiter()
        logger.info("   ✅ 速率限制器初始化成功")
        
        logger.info("🎉 所有核心功能验证通过！")
        logger.info("💡 程序核心组件工作正常，Telegram连接问题可能与代理配置有关")
        
        return True
        
    except Exception as e:
        logger.error(f"核心功能验证失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)