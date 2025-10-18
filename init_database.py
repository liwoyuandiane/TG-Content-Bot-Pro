#!/usr/bin/env python3
"""
数据库初始化脚本
用于在首次安装后初始化MongoDB数据库结构和索引
"""

import sys
import os
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入项目模块
try:
    from main.core.database import DatabaseManager
    import logging
    from decouple import config
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s'
    )
    logger = logging.getLogger(__name__)
    
except ImportError as e:
    print(f"导入模块失败: {e}")
    sys.exit(1)

async def initialize_database():
    """初始化数据库"""
    try:
        logger.info("开始初始化数据库...")
        
        # 检查MongoDB连接字符串
        mongo_db_uri = config("MONGO_DB", default=None)
        if not mongo_db_uri:
            logger.error("未配置MongoDB连接字符串")
            return False
            
        # 创建数据库管理器实例
        db_manager = DatabaseManager()
        
        # 检查连接是否成功
        if db_manager.db is None:
            logger.error("数据库连接失败")
            return False
            
        logger.info("数据库连接成功")
        
        # 创建索引
        logger.info("创建数据库索引...")
        db_manager._create_indexes()
        
        # 初始化默认配置
        logger.info("初始化默认配置...")
        
        # 初始化流量限制配置
        try:
            # 检查是否已存在流量限制配置
            traffic_limit = db_manager.db.traffic_limits.find_one()
            if not traffic_limit:
                # 创建默认流量限制配置
                default_limits = {
                    "daily_limit": 1073741824,  # 1GB
                    "monthly_limit": 10737418240,  # 10GB
                    "per_file_limit": 104857600,  # 100MB
                    "enabled": 1  # 默认启用
                }
                db_manager.db.traffic_limits.insert_one(default_limits)
                logger.info("已创建默认流量限制配置")
            else:
                logger.info("流量限制配置已存在")
        except Exception as e:
            logger.warning(f"初始化流量限制配置时出错: {e}")
        
        # 初始化其他默认配置
        try:
            # 检查是否已存在全局配置
            global_config = db_manager.db.settings.find_one({"config_type": "global"})
            if not global_config:
                # 创建默认全局配置
                default_config = {
                    "config_type": "global",
                    "version": "1.0",
                    "created_at": "2024-01-01"
                }
                db_manager.db.settings.insert_one(default_config)
                logger.info("已创建默认全局配置")
            else:
                logger.info("全局配置已存在")
        except Exception as e:
            logger.warning(f"初始化全局配置时出错: {e}")
        
        logger.info("数据库初始化完成！")
        return True
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return False

def main():
    """主函数"""
    try:
        # 运行异步初始化函数
        result = asyncio.run(initialize_database())
        if result:
            print("\n✅ 数据库初始化成功！")
            sys.exit(0)
        else:
            print("\n❌ 数据库初始化失败！")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 初始化过程中发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()