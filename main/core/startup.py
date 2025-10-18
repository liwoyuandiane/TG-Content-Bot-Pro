#!/usr/bin/env python3
"""程序启动脚本 - 正确处理环境变量加载"""

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
                'ENCRYPTION_KEY', 'MAX_WORKERS', 'CHUNK_SIZE',
                'DEFAULT_DAILY_LIMIT', 'DEFAULT_MONTHLY_LIMIT', 
                'DEFAULT_PER_FILE_LIMIT', 'DEBUG', 'LOG_LEVEL'
            ]
            
            loaded_vars = []
            for key in env_vars:
                try:
                    value = env_config(key)
                    os.environ[key] = str(value)
                    loaded_vars.append(key)
                except Exception:
                    pass  # 变量不存在，跳过
            
            logger.info(f"成功加载 {len(loaded_vars)} 个环境变量: {', '.join(loaded_vars)}")
            return True
        else:
            logger.warning(f"环境文件不存在: {env_path}")
            return False
    except Exception as e:
        logger.error(f"加载环境变量时出错: {e}")
        return False

def main():
    """主函数"""
    logger.info("开始启动SaveRestrictedContentBot...")
    
    # 加载环境变量
    if not load_environment_variables():
        logger.warning("环境变量加载失败，将继续使用系统环境变量")
    
    # 添加项目路径
    project_path = '/data/SaveRestrictedContentBot'
    if project_path not in sys.path:
        sys.path.insert(0, project_path)
    
    try:
        # 导入主应用
        from main.app import main as app_main
        logger.info("成功导入主应用")
        
        # 运行主应用
        logger.info("启动主应用...")
        app_main()
        
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在退出...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"启动应用时出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()