#!/usr/bin/env python3
"""
简单的数据库测试脚本
用于测试MongoDB连接而不依赖完整的配置
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入必要的模块
try:
    from main.core.database import DatabaseManager
    from decouple import config
    import logging
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s'
    )
    logger = logging.getLogger(__name__)
    
except ImportError as e:
    print(f"导入模块失败: {e}")
    sys.exit(1)

def test_database_connection():
    """测试数据库连接"""
    try:
        logger.info("开始测试数据库连接...")
        
        # 检查MongoDB连接字符串
        mongo_db_uri = config("MONGO_DB", default=None)
        if not mongo_db_uri:
            logger.error("未配置MongoDB连接字符串")
            return False
            
        logger.info(f"MongoDB连接字符串: {mongo_db_uri[:50]}...")
        
        # 创建数据库管理器实例
        db_manager = DatabaseManager()
        
        # 检查连接是否成功
        if db_manager.db is None:
            logger.error("数据库连接失败")
            return False
            
        logger.info("数据库连接成功")
        
        # 测试基本操作
        try:
            # 测试ping命令
            db_manager.client.admin.command('ping')
            logger.info("数据库ping测试成功")
            
            # 测试列出集合
            collections = db_manager.db.list_collection_names()
            logger.info(f"数据库集合: {collections}")
            
        except Exception as e:
            logger.error(f"数据库操作测试失败: {e}")
            return False
            
        logger.info("数据库连接测试完成！")
        return True
        
    except Exception as e:
        logger.error(f"数据库连接测试失败: {e}")
        return False

if __name__ == "__main__":
    result = test_database_connection()
    if result:
        print("\n✅ 数据库连接测试成功！")
        sys.exit(0)
    else:
        print("\n❌ 数据库连接测试失败！")
        sys.exit(1)