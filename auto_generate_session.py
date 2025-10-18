#!/usr/bin/env python3
"""
自动 SESSION 生成器
使用 .env 中配置的 API 凭证
"""

from pyrogram import Client
from decouple import config
import asyncio

async def generate_session():
    # 从 .env 读取配置
    API_ID = config("API_ID", cast=int)
    API_HASH = config("API_HASH")
    
    print("=" * 60)
    print("Pyrogram Session 自动生成器")
    print("=" * 60)
    print(f"\n✅ API_ID: {API_ID}")
    print(f"✅ API_HASH: {API_HASH[:10]}...")
    print("\n现在将启动交互式会话生成流程...")
    print("请准备好您的手机号和验证码")
    print("=" * 60)
    
    # 创建客户端（使用 with 语句自动处理登录流程）
    async with Client(
        "session_generator",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True
    ) as app:
        # 导出 SESSION 字符串
        session_string = await app.export_session_string()
        
        print("\n" + "=" * 60)
        print("✅ SESSION 生成成功！")
        print("=" * 60)
        print("\n您的 SESSION 字符串：\n")
        print(session_string)
        print("\n" + "=" * 60)
        print("请将此字符串保存到 .env 文件的 SESSION= 中")
        print("⚠️ 请妥善保管，不要泄露给他人！")
        print("=" * 60)
        
        return session_string

if __name__ == "__main__":
    try:
        asyncio.run(generate_session())
    except KeyboardInterrupt:
        print("\n\n已取消")
    except Exception as e:
        print(f"\n\n❌ 错误: {e}")
