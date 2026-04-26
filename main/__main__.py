"""应用入口"""
import os
import sys

if os.path.exists('.env'):
    try:
        from decouple import Config, RepositoryEnv
        env_config = Config(RepositoryEnv('.env'))
        for key in ['API_ID', 'API_HASH', 'BOT_TOKEN', 'AUTH', 'MONGO_DB', 'FORCESUB', 'SESSION', 'HEALTH_CHECK_PORT']:
            try:
                os.environ[key] = str(env_config(key))
            except Exception:
                pass
    except Exception:
        pass

from .app import main

if __name__ == '__main__':
    main()