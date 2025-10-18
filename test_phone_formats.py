from pyrogram import Client
import asyncio

async def test_different_accounts():
    API_ID = 21722171
    API_HASH = "6dc06adcb5961d617c347d7776d2ec76"
    
    print("=" * 60)
    print("测试不同账号和验证码发送方式")
    print("=" * 60)
    
    client = Client(
        "test_account",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True
    )
    
    try:
        await client.connect()
        
        # 测试1: 尝试强制使用短信
        phone = "+16828004917"
        print(f"\n测试手机号: {phone}")
        print("尝试发送验证码...")
        
        try:
            # 第一次发送
            sent_code = await client.send_code(phone)
            print(f"\n第一次发送:")
            print(f"  类型: {sent_code.type}")
            print(f"  Hash: {sent_code.phone_code_hash[:30]}...")
            print(f"  下一种类型: {sent_code.next_type}")
            print(f"  超时: {sent_code.timeout}")
            
            # 等待5秒
            await asyncio.sleep(5)
            
            # 尝试重新发送以切换到短信
            print(f"\n尝试重新发送(切换到短信)...")
            sent_code2 = await client.resend_code(phone, sent_code.phone_code_hash)
            print(f"  类型: {sent_code2.type}")
            print(f"  Hash: {sent_code2.phone_code_hash[:30]}...")
            print(f"  下一种类型: {sent_code2.next_type}")
            
        except Exception as e:
            error_str = str(e)
            print(f"\n❌ 错误: {type(e).__name__}")
            print(f"详细: {error_str}")
            
            if "FLOOD_WAIT" in error_str or "FLOOD" in error_str:
                import re
                wait_time = re.search(r'(\d+)', error_str)
                if wait_time:
                    seconds = int(wait_time.group(1))
                    minutes = seconds // 60
                    hours = minutes // 60
                    print(f"\n⚠️ 您被限流了！")
                    print(f"需要等待: {seconds} 秒")
                    if hours > 0:
                        print(f"        = {hours} 小时 {minutes % 60} 分钟")
                    elif minutes > 0:
                        print(f"        = {minutes} 分钟")
                    print(f"\n原因: 短时间内发送了太多验证码请求")
                    print(f"建议: 等待指定时间后再试，或使用其他手机号")
            elif "PHONE_NUMBER_BANNED" in error_str:
                print("\n⚠️ 此手机号已被 Telegram 封禁！")
                print("建议: 使用其他手机号")
            elif "PHONE_NUMBER_INVALID" in error_str:
                print("\n⚠️ 手机号格式无效！")
            
    finally:
        await client.disconnect()
        print("\n" + "=" * 60)

asyncio.run(test_different_accounts())
