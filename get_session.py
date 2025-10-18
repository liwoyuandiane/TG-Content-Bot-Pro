#!/usr/bin/env python3
"""
Pyrogram Session String Generator
用于生成Telegram Pyrogram会话字符串
"""

from pyrogram import Client

print("=" * 50)
print("Pyrogram Session String Generator")
print("Pyrogram 会话字符串生成器")
print("=" * 50)

API_ID = input("\n请输入 API_ID: ").strip()
API_HASH = input("请输入 API_HASH: ").strip()

if not API_ID or not API_HASH:
    print("\n错误：API_ID 和 API_HASH 不能为空！")
    exit(1)

try:
    API_ID = int(API_ID)
except ValueError:
    print("\n错误：API_ID 必须是数字！")
    exit(1)

print("\n正在生成会话字符串...")
print("您需要输入手机号码和验证码\n")

with Client(
    name="session_generator",
    api_id=API_ID,
    api_hash=API_HASH,
    in_memory=True
) as app:
    session_string = app.export_session_string()
    
    print("\n" + "=" * 50)
    print("会话字符串生成成功！")
    print("=" * 50)
    print("\n您的 SESSION 字符串：")
    print(f"\n{session_string}\n")
    print("=" * 50)
    print("\n请复制上面的字符串并保存到 .env 文件中")
    print("注意：请妥善保管此字符串，不要泄露给他人！")
    print("=" * 50)
