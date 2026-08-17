"""应用入口"""
import os
import sys

if os.path.exists('.env'):
    try:
        from decouple import Config, RepositoryEnv
        env_config = Config(RepositoryEnv('.env'))
        # 主要配置键（必需）
        main_keys = ['API_ID', 'API_HASH', 'BOT_TOKEN', 'AUTH', 'MONGO_DB']
        # 可选配置键
        optional_keys = ['FORCESUB', 'SESSION', 'HEALTH_CHECK_PORT', 'ENCRYPTION_KEY', 
                     'LOG_LEVEL', 'DEBUG', 'ENVIRONMENT', 'DB_RESET', 'SESSION_DIR']
        for key in main_keys + optional_keys:
            try:
                os.environ[key] = str(env_config(key))
            except Exception:
                pass
    except Exception:
        pass

from .app import main

if __name__ == '__main__':
    main()