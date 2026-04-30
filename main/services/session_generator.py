"""SESSION 自动生成器"""
import asyncio
import logging
import re
from typing import Tuple, Optional, Dict, Any

from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded
from ..config import settings

logger = logging.getLogger(__name__)


class SessionGenerator:
    """SESSION 自动生成器"""
    
    def __init__(self):
        self.pending_logins: Dict[str, Dict[str, Any]] = {}
    
    async def send_verification_code(self, phone_number: str) -> Tuple[bool, str]:
        """发送验证码到手机号"""
        logger.info(f"发送验证码到: {phone_number[:7]}***")
        
        try:
            client = Client(
                name="temp_session",
                api_hash=settings.API_HASH,
                api_id=settings.API_ID,
                app_version="TG-Content-Bot-Pro",
                device_model="Bot",
                system_version="Linux",
                lang_code="zh",
                in_memory=True
            )
            
            await client.connect()
            logger.info("已连接到 Telegram")
            
            result = await client.send_code(phone_number)
            logger.info(f"验证码发送成功，hash: {result.phone_code_hash[:10]}...")
            
            self.pending_logins[phone_number] = {
                "client": client,
                "phone_code_hash": result.phone_code_hash,
                "phone_number": phone_number,
                "state": "waiting_code"
            }
            
            return True, "请回复收到的验证码（如 1 2 3 4 5）"
            
        except Exception as e:
            logger.error(f"发送验证码失败: {e}", exc_info=True)
            return False, f"发送失败: {str(e)}"
    
    async def verify_and_get_session(self, phone_number: str, code: str) -> Tuple[bool, str]:
        """验证验证码并获取 session"""
        logger.info(f"验证验证码: phone={phone_number[:7]}***, code={code}")
        
        if phone_number not in self.pending_logins:
            logger.error(f"找不到手机号 {phone_number[:7]}*** 的登录记录")
            return False, "请先发送手机号"
        
        info = self.pending_logins[phone_number]
        client = info["client"]
        phone_code_hash = info["phone_code_hash"]
        
        try:
            # 确保客户端已连接
            if not client.is_connected:
                logger.info("客户端未连接，重新连接...")
                await client.connect()
            
            logger.info("正在调用 sign_in...")
            session = await client.sign_in(
                phone_number,
                phone_code_hash,
                code
            )
            
            logger.info("sign_in 成功，导出 session...")
            session_string = client.export_session_string()
            logger.info(f"Session 导出成功，长度: {len(session_string)}")
            
            await client.disconnect()
            del self.pending_logins[phone_number]
            
            return True, session_string
            
        except SessionPasswordNeeded:
            # 两步验证需要密码
            logger.info("用户启用了两步验证，需要密码")
            info["state"] = "waiting_password"
            return False, "NEED_PASSWORD"
            
        except Exception as e:
            logger.error(f"验证失败: {type(e).__name__}: {e}", exc_info=True)
            try:
                await client.disconnect()
            except:
                pass
            if phone_number in self.pending_logins:
                del self.pending_logins[phone_number]
            return False, f"验证码错误: {type(e).__name__}"
    
    async def verify_password(self, phone_number: str, password: str) -> Tuple[bool, str]:
        """验证两步验证密码"""
        logger.info(f"验证两步验证密码: phone={phone_number[:7]}***")
        
        if phone_number not in self.pending_logins:
            return False, "请先发送手机号"
        
        info = self.pending_logins[phone_number]
        client = info["client"]
        
        try:
            if not client.is_connected:
                await client.connect()
            
            logger.info("正在调用 check_password...")
            await client.check_password(password)
            
            logger.info("密码验证成功，导出 session...")
            session_string = await client.export_session_string()
            logger.info(f"Session 导出成功，长度: {len(session_string)}")
            
            await client.disconnect()
            del self.pending_logins[phone_number]
            
            return True, session_string
            
        except Exception as e:
            logger.error(f"密码验证失败: {type(e).__name__}: {e}", exc_info=True)
            try:
                await client.disconnect()
            except:
                pass
            if phone_number in self.pending_logins:
                del self.pending_logins[phone_number]
            return False, f"密码错误: {type(e).__name__}"


session_generator = SessionGenerator()


async def generate_session_by_phone(phone_number: str) -> Tuple[bool, str]:
    """通过手机号生成 SESSION - 第一步"""
    return await session_generator.send_verification_code(phone_number)


async def verify_phone_code(phone_number: str, code: str) -> Tuple[bool, str]:
    """验证验证码并获取 session - 第二步"""
    return await session_generator.verify_and_get_session(phone_number, code)


async def verify_password(phone_number: str, password: str) -> Tuple[bool, str]:
    """验证两步验证密码 - 第三步"""
    return await session_generator.verify_password(phone_number, password)