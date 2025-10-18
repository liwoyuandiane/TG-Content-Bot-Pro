#!/usr/bin/env python3
"""程序启动脚本"""

import os
import sys

# 添加项目路径
project_path = '/data/SaveRestrictedContentBot'
if project_path not in sys.path:
    sys.path.insert(0, project_path)

def load_environment_variables():
    """手动加载环境变量"""
    try:
        from decouple import Config, RepositoryEnv
        env_path = os.path.join(os.getcwd(), '.env')
        if os.path.exists(env_path):
            print(f"加载环境文件: {env_path}")
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
                    print(f"设置环境变量 {key}")
                except Exception:
                    pass  # 变量不存在，跳过
            return True
        else:
            print(f"环境文件不存在: {env_path}")
            return False
    except Exception as e:
        print(f"加载环境变量时出错: {e}")
        return False

def main():
    """主函数"""
    print("开始启动程序...")
    
    # 加载环境变量
    if not load_environment_variables():
        print("警告: 环境变量加载失败")
    
    # 测试环境变量
    print("\n=== 启动前环境变量检查 ===")
    proxy_vars = ['TELEGRAM_PROXY_SCHEME', 'TELEGRAM_PROXY_HOST', 'TELEGRAM_PROXY_PORT']
    for var in proxy_vars:
        value = os.environ.get(var, '未设置')
        print(f"{var}: {value}")
    
    # 导入并运行主应用
    try:
        from main.app import main as app_main
        print("成功导入主应用")
        app_main()
    except KeyboardInterrupt:
        print("程序被用户中断")
    except Exception as e:
        print(f"启动应用时出错: {e}")

if __name__ == "__main__":
    main()