from pyrogram import Client
import asyncio
from datetime import datetime

async def comprehensive_test():
    API_ID = 21722171
    API_HASH = "6dc06adcb5961d617c347d7776d2ec76"
    
    print("\n" + "=" * 70)
    print(" Telegram 验证码问题综合诊断报告 ")
    print("=" * 70)
    print(f"诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    client = Client(
        "diagnosis",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True
    )
    
    try:
        await client.connect()
        print("\n✅ 步骤 1: API 连接成功")
        
        phone = "+16828004917"
        print(f"✅ 步骤 2: 测试手机号 {phone}")
        
        # 发送验证码
        sent_code = await client.send_code(phone)
        print(f"✅ 步骤 3: 验证码发送成功")
        
        print("\n" + "-" * 70)
        print(" 验证码发送详情 ")
        print("-" * 70)
        print(f"发送方式: {sent_code.type}")
        print(f"验证码哈希: {sent_code.phone_code_hash[:40]}...")
        print(f"超时时间: {sent_code.timeout if sent_code.timeout else '无限制'}")
        print(f"备用方式: {sent_code.next_type if sent_code.next_type else '无'}")
        
        print("\n" + "-" * 70)
        print(" 诊断结果 ")
        print("-" * 70)
        
        code_type = str(sent_code.type)
        
        if "APP" in code_type.upper():
            print("\n📱 验证码类型: Telegram 应用内消息")
            print("\n⚠️  可能的原因分析:")
            print("   1. 您的 Telegram 账号可能启用了 \"安全模式\"")
            print("   2. 该手机号可能关联了多个设备，验证码发到了其他设备")
            print("   3. Telegram 通知被系统或应用设置屏蔽")
            print("   4. 账号可能有登录限制(频繁登录/多设备)")
            
            print("\n💡 解决方案:")
            print("   方案1: 检查所有已登录的 Telegram 设备")
            print("   方案2: 尝试在 Telegram 官方应用中查看 \"Devices\" 页面")
            print("   方案3: 使用 Telegram Desktop 或 Web 版本登录查看")
            print("   方案4: 等待 30-60 分钟后重试")
            print("   方案5: 使用另一个手机号测试")
            
            print("\n⚠️  特别提示:")
            print("   • 如果该号码之前频繁生成 SESSION，可能被临时限制")
            print("   • Telegram 对同一号码的验证码请求有频率限制")
            print("   • 建议: 间隔至少 1 小时后再次尝试")
        
        print("\n" + "=" * 70)
        print(" 建议操作 ")
        print("=" * 70)
        print("\n1. 立即操作:")
        print("   - 检查所有已登录 Telegram 的设备")
        print("   - 查看手机系统通知设置")
        print("   - 尝试重启 Telegram 应用")
        
        print("\n2. 替代方案:")
        print("   - 使用其他手机号进行测试")
        print("   - 在 Telegram 官方客户端直接登录")
        print("   - 使用命令行工具 get_session.py 生成 SESSION")
        
        print("\n3. 如果仍无法解决:")
        print("   - 可能是 Telegram 对该号码的临时限制")
        print("   - 建议等待 24 小时后重试")
        print("   - 或联系 Telegram 支持")
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"\n❌ 错误: {type(e).__name__}")
        print(f"详细信息: {str(e)}")
    finally:
        await client.disconnect()

asyncio.run(comprehensive_test())
