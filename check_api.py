from pyrogram import Client
import asyncio

async def check_api():
    API_ID = 21722171
    API_HASH = "6dc06adcb5961d617c347d7776d2ec76"
    
    print("=" * 60)
    print("检查 Telegram API 配置状态")
    print("=" * 60)
    
    client = Client(
        "test_check",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True
    )
    
    try:
        await client.connect()
        print("✅ API 连接成功")
        print(f"✅ API_ID: {API_ID}")
        print(f"✅ API_HASH: {API_HASH[:10]}...")
        
        # 测试不同的手机号格式
        test_phones = [
            "+16828004917",
            "+1 682 800 4917",
            "+1-682-800-4917"
        ]
        
        print("\n" + "=" * 60)
        print("测试发送验证码...")
        print("=" * 60)
        
        for phone in test_phones:
            print(f"\n尝试发送到: {phone}")
            try:
                sent_code = await client.send_code(phone)
                print(f"  ✅ 成功! 类型: {sent_code.type}")
                print(f"  Hash: {sent_code.phone_code_hash[:30]}...")
                if sent_code.timeout:
                    print(f"  超时: {sent_code.timeout} 秒")
                print(f"  下一种验证方式: {sent_code.next_type}")
                break
            except Exception as e:
                print(f"  ❌ 失败: {e}")
        
    except Exception as e:
        print(f"\n❌ 错误: {type(e).__name__}")
        print(f"详细信息: {e}")
        
        if "FLOOD" in str(e).upper():
            print("\n⚠️ 您可能被限流了！")
            print("原因: 短时间内发送了太多验证码请求")
            print("解决: 等待几小时后再试")
        elif "PHONE_NUMBER_INVALID" in str(e).upper():
            print("\n⚠️ 手机号无效！")
        elif "API_ID_INVALID" in str(e).upper():
            print("\n⚠️ API_ID 或 API_HASH 无效！")
            print("请从 https://my.telegram.org 重新获取")
    finally:
        await client.disconnect()
        print("\n" + "=" * 60)

asyncio.run(check_api())
