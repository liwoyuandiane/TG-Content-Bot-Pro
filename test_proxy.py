#!/usr/bin/env python3
"""
代理配置测试脚本
用于测试 SOCKS5 和 HTTP 代理连接
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入项目模块
try:
    from main.config import settings
    from main.core.clients import client_manager
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

async def test_proxy_configuration():
    """测试代理配置"""
    try:
        logger.info("开始测试代理配置...")
        
        # 显示代理配置
        proxy_config = client_manager.proxy_config
        if proxy_config:
            logger.info(f"检测到代理配置: {proxy_config}")
            
            # 测试代理连接
            logger.info("正在测试代理连接...")
            
            # 获取Telethon代理配置
            telethon_proxy = client_manager._get_telethon_proxy()
            if telethon_proxy:
                logger.info(f"Telethon代理配置: {telethon_proxy}")
            
            # 获取Pyrogram代理配置
            pyrogram_proxy = client_manager._get_pyrogram_proxy()
            if pyrogram_proxy:
                pyrogram_config = client_manager._create_pyrogram_proxy_config(pyrogram_proxy)
                logger.info(f"Pyrogram代理配置: {pyrogram_config}")
                
            logger.info("代理配置测试完成")
            return True
        else:
            logger.info("未检测到代理配置")
            return False
            
    except Exception as e:
        logger.error(f"代理配置测试失败: {e}")
        return False

def main():
    """主函数"""
    try:
        # 运行异步测试函数
        result = asyncio.run(test_proxy_configuration())
        if result:
            print("\n✅ 代理配置测试成功！")
            sys.exit(0)
        else:
            print("\n⚠️  未检测到代理配置或测试未完成")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()