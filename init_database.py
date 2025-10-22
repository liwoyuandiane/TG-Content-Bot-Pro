#!/usr/bin/env python3
"""
数据库初始化脚本
用于在首次安装后初始化MongoDB数据库结构和索引
"""

import sys
import os
import asyncio
from pathlib import Path
from decouple import config

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
import logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# 简化版数据库管理器，只用于初始化
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError, ServerSelectionTimeoutError

class SimpleDatabaseManager:
    """简化版数据库管理器"""
    
    def __init__(self, mongo_uri):
        """初始化数据库管理器"""
        self.client = None
        self.db = None
        self.mongo_uri = mongo_uri
        self._connect()
    
    def _connect(self):
        """连接到MongoDB数据库"""
        if not self.mongo_uri:
            logger.warning("未配置MongoDB连接字符串")
            return
        
        try:
            logger.info("正在连接MongoDB...")
            self.client = MongoClient(
                self.mongo_uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                maxPoolSize=10,
                minPoolSize=2,
                socketTimeoutMS=5000,
                connect=False
            )
            # 测试连接
            self.client.admin.command('ping')
            self.db = self.client['tg_content_bot']
            logger.info("MongoDB数据库连接成功")
        except Exception as e:
            logger.error(f"MongoDB数据库连接失败: {e}")
            self.client = None
            self.db = None
    
    def _create_indexes(self):
        """创建数据库索引"""
        if not self.db:
            logger.error("数据库未连接")
            return
        
        try:
            # users 集合索引
            self.db.users.create_index("user_id", unique=True)
            self.db.users.create_index("username")
            self.db.users.create_index("is_banned")
            self.db.users.create_index("join_date")
            logger.info("users 集合索引创建完成")
            
            # download_history 集合索引
            self.db.download_history.create_index("message_id")
            self.db.download_history.create_index("chat_id")
            self.db.download_history.create_index("user_id")
            self.db.download_history.create_index("timestamp")
            self.db.download_history.create_index("status")
            self.db.download_history.create_index([("user_id", 1), ("timestamp", -1)])
            logger.info("download_history 集合索引创建完成")
            
            # user_stats 集合索引
            self.db.user_stats.create_index("user_id", unique=True)
            logger.info("user_stats 集合索引创建完成")
            
            # batch_tasks 集合索引
            self.db.batch_tasks.create_index("task_id", unique=True)
            self.db.batch_tasks.create_index("user_id")
            self.db.batch_tasks.create_index("status")
            self.db.batch_tasks.create_index("created_at")
            logger.info("batch_tasks 集合索引创建完成")
            
            # user_traffic 集合索引
            self.db.user_traffic.create_index("user_id")
            self.db.user_traffic.create_index("date")
            self.db.user_traffic.create_index("month")
            self.db.user_traffic.create_index([("user_id", 1), ("date", -1)])
            self.db.user_traffic.create_index([("user_id", 1), ("month", -1)])
            logger.info("user_traffic 集合索引创建完成")
            
            # traffic_limits 集合索引
            self.db.traffic_limits.create_index("config_name", unique=True)
            logger.info("traffic_limits 集合索引创建完成")
            
            # settings 集合索引
            self.db.settings.create_index("config_type", unique=True)
            logger.info("settings 集合索引创建完成")
            
            # sessions 集合索引
            self.db.sessions.create_index("user_id", unique=True)
            self.db.sessions.create_index("created_at")
            logger.info("sessions 集合索引创建完成")
            
        except Exception as e:
            logger.error(f"创建数据库索引时出错: {e}")
    
    def initialize_collections(self):
        """初始化数据库集合和默认数据"""
        if self.db is None:
            logger.error("数据库未连接")
            return False
            
        try:
            logger.info("创建数据库索引...")
            self._create_indexes()
            
            # 初始化流量限制配置
            logger.info("初始化默认配置...")
            
            # 初始化流量限制配置
            try:
                # 检查是否已存在流量限制配置
                traffic_limit = self.db.traffic_limits.find_one()
                if not traffic_limit:
                    # 创建默认流量限制配置
                    default_limits = {
                        "config_name": "default",
                        "daily_limit": 1073741824,  # 1GB
                        "monthly_limit": 10737418240,  # 10GB
                        "per_file_limit": 104857600,  # 100MB
                        "enabled": True  # 默认启用
                    }
                    self.db.traffic_limits.insert_one(default_limits)
                    logger.info("已创建默认流量限制配置")
                else:
                    logger.info("流量限制配置已存在")
            except Exception as e:
                logger.warning(f"初始化流量限制配置时出错: {e}")
            
            # 初始化其他默认配置
            try:
                # 检查是否已存在全局配置
                global_config = self.db.settings.find_one({"config_type": "global"})
                if not global_config:
                    # 创建默认全局配置
                    default_config = {
                        "config_type": "global",
                        "version": "1.0",
                        "created_at": "2024-01-01"
                    }
                    self.db.settings.insert_one(default_config)
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

async def initialize_database():
    """初始化数据库"""
    try:
        logger.info("开始初始化数据库...")
        
        # 检查MongoDB连接字符串
        mongo_db_uri = config("MONGO_DB", default=None)
        if not mongo_db_uri:
            logger.error("未配置MongoDB连接字符串")
            return False
            
        # 创建简化版数据库管理器实例
        db_manager = SimpleDatabaseManager(mongo_db_uri)
        
        # 检查连接是否成功
        if db_manager.db is None:
            logger.error("数据库连接失败")
            return False
            
        # 初始化集合和默认数据
        result = db_manager.initialize_collections()
        return result
        
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