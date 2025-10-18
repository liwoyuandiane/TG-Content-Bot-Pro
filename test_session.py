from pyrogram import Client
import asyncio

async def test_send_code():
    API_ID = 21722171
    API_HASH = "6dc06adcb5961d617c347d7776d2ec76"
    
    client = Client(
        "test_temp",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True
    )
    
    try:
        await client.connect()
        print("客户端已连接")
        
        phone = input("请输入手机号 (例如 +1234567890): ")
        print(f"正在发送验证码到 {phone}...")
        
        sent_code = await client.send_code(phone)
        print(f"验证码已发送!")
        print(f"类型: {sent_code.type}")
        print(f"Hash: {sent_code.phone_code_hash[:20]}...")
        print(f"超时: {sent_code.timeout}")
        
        code = input("请输入验证码: ")
        await client.sign_in(phone, sent_code.phone_code_hash, code.replace(" ", ""))
        
        session = await client.export_session_string()
        print(f"\nSESSION: {session}")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()

asyncio.run(test_send_code())
