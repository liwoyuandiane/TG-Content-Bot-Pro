#!/usr/bin/env python3
"""
交互式 SESSION 生成 - 手动输入验证码
"""

from pyrogram import Client
import asyncio
from decouple import config

async def interactive_generate():
    API_ID = config("API_ID", cast=int)
    API_HASH = config("API_HASH")
    
    print("\n" + "=" * 70)
    print(" Pyrogram SESSION 交互式生成器 ".center(70))
    print("=" * 70)
    
    print(f"\n✅ 使用配置:")
    print(f"   API_ID: {API_ID}")
    print(f"   API_HASH: {API_HASH[:15]}...")
    
    # 获取手机号
    phone = input("\n📱 请输入手机号 (包含国家代码，例如 +1234567890): ").strip()
    
    if not phone.startswith('+'):
        print("❌ 手机号必须以 + 开头")
        return
    
    client = Client(
        "temp_session",
        api_id=API_ID,
        api_hash=API_HASH,
        phone_number=phone,
        in_memory=True
    )
    
    try:
        await client.connect()
        print("\n✅ 客户端已连接")
        
        # 发送验证码
        print(f"📤 正在发送验证码到 {phone}...")
        sent_code = await client.send_code(phone)
        
        print(f"\n✅ 验证码已发送！")
        print(f"   方式: {sent_code.type}")
        print(f"   验证码哈希: {sent_code.phone_code_hash[:30]}...")
        
        if "APP" in str(sent_code.type).upper():
            print("\n📱 验证码通过 Telegram 应用内消息发送")
            print("   请在 Telegram 中查找 'Telegram' 官方账号的消息")
        elif "SMS" in str(sent_code.type).upper():
            print("\n📱 验证码通过短信发送")
            print("   请查看手机短信")
        
        # 输入验证码
        code = input("\n🔑 请输入验证码 (可以用空格分隔，例如 1 2 3 4 5): ").strip()
        code = code.replace(' ', '').replace('-', '')
        
        print("\n⏳ 正在验证...")
        
        try:
            # 尝试登录
            await client.sign_in(phone, sent_code.phone_code_hash, code)
            print("✅ 登录成功！")
        except Exception as e:
            if "password" in str(e).lower() or "SessionPasswordNeeded" in str(e):
                # 需要两步验证密码
                print("\n🔐 检测到两步验证")
                password = input("请输入两步验证密码: ").strip()
                await client.check_password(password)
                print("✅ 密码验证成功！")
            else:
                raise
        
        # 导出 SESSION
        print("\n📤 正在生成 SESSION 字符串...")
        session_string = await client.export_session_string()
        
        print("\n" + "=" * 70)
        print(" ✅ SESSION 生成成功！ ".center(70))
        print("=" * 70)
        print("\n您的 SESSION 字符串：\n")
        print(session_string)
        print("\n" + "=" * 70)
        print("📋 使用方法:")
        print("   1. 复制上面的 SESSION 字符串")
        print("   2. 打开 .env 文件")
        print("   3. 设置: SESSION=<粘贴的字符串>")
        print("   4. 重启机器人")
        print("\n⚠️  安全提示: 请妥善保管此字符串，不要泄露！")
        print("=" * 70 + "\n")
        
        return session_string
        
    except Exception as e:
        print(f"\n❌ 错误: {type(e).__name__}")
        print(f"   详细: {str(e)}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(interactive_generate())
    except KeyboardInterrupt:
        print("\n\n⚠️ 已取消")
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
