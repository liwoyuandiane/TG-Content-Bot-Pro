"""应用主入口"""
import sys
import logging
import asyncio
import os

# 手动加载环境变量
try:
    from decouple import Config, RepositoryEnv
    env_path = os.path.join(os.getcwd(), '.env')
    if os.path.exists(env_path):
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
            except Exception:
                pass  # 变量不存在，跳过
except Exception:
    pass  # decouple库不可用，跳过

# 设置日志
log_level_name = os.getenv('LOG_LEVEL', 'WARNING')
log_level = getattr(logging, log_level_name.upper(), logging.WARNING)
logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=log_level)

from .app import main

if __name__ == "__main__":
    main()