#!/usr/bin/env python3
"""完整的程序测试脚本"""

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

# 导入项目模块
try:
    from main.app import startup, shutdown
    from main.core.clients import client_manager
    logger.info("成功导入项目模块")
except Exception as e:
    logger.error(f"导入项目模块时出错: {e}")
    sys.exit(1)

async def test_program():
    """测试程序启动"""
    try:
        logger.info("开始测试程序启动...")
        
        # 初始化客户端
        logger.info("初始化客户端...")
        await client_manager.initialize_clients()
        
        logger.info("程序启动测试成功完成")
        return True
        
    except Exception as e:
        logger.error(f"程序启动测试失败: {e}")
        return False
    finally:
        # 确保关闭客户端
        try:
            await shutdown()
        except Exception as e:
            logger.error(f"关闭客户端时出错: {e}")

if __name__ == "__main__":
    logger.info("开始运行程序测试...")
    
    try:
        result = asyncio.run(test_program())
        if result:
            logger.info("✅ 程序测试成功")
            sys.exit(0)
        else:
            logger.error("❌ 程序测试失败")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在退出...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"运行测试时出错: {e}")
        sys.exit(1)