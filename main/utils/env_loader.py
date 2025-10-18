#!/usr/bin/env python3
"""手动加载环境变量的脚本"""

import os
from decouple import Config, RepositoryEnv

def load_env_file():
    """手动加载.env文件"""
    env_path = os.path.join(os.getcwd(), '.env')
    if os.path.exists(env_path):
        print(f"加载环境文件: {env_path}")
        env_config = Config(RepositoryEnv(env_path))
        
        # 将环境变量设置到os.environ中
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
                print(f"设置 {key} = {str(value)[:50]}{'...' if len(str(value)) > 50 else ''}")
            except Exception as e:
                print(f"跳过 {key}: {e}")
    else:
        print(f"环境文件不存在: {env_path}")

if __name__ == "__main__":
    load_env_file()