#!/usr/bin/env python3
"""测试SOCKS5代理配置"""

import os
import sys

def test_socks5_proxy_config():
    """测试SOCKS5代理配置"""
    print("测试SOCKS5代理配置...")
    
    # 模拟SOCKS5代理配置
    proxy_configs = [
        {
            'scheme': 'socks5',
            'hostname': 'proxy.example.com',
            'port': 1080
        },
        {
            'scheme': 'socks4',
            'hostname': 'proxy.example.com',
            'port': 1080
        },
        {
            'scheme': 'http',
            'hostname': 'proxy.example.com',
            'port': 8080
        },
        {
            'scheme': 'https',
            'hostname': 'proxy.example.com',
            'port': 443
        }
    ]
    
    # 添加项目路径
    project_path = '/data/SaveRestrictedContentBot'
    if project_path not in sys.path:
        sys.path.insert(0, project_path)
    
    from main.core.clients import ClientManager
    
    for i, config in enumerate(proxy_configs):
        print(f"\n测试配置 {i+1}: {config['scheme']}://{config['hostname']}:{config['port']}")
        
        # 创建模拟的客户端管理器
        client_manager = ClientManager()
        client_manager._proxy_config = config
        
        # 测试Telethon代理配置
        telethon_proxy = client_manager._get_telethon_proxy()
        print(f"  Telethon代理配置: {telethon_proxy}")
        
        # 测试Pyrogram代理配置
        pyrogram_proxy = client_manager._get_pyrogram_proxy()
        print(f"  Pyrogram代理配置: {pyrogram_proxy}")

if __name__ == "__main__":
    test_socks5_proxy_config()