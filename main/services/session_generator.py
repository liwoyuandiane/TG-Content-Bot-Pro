"""SESSION 自动生成器"""
import asyncio
import logging
import re
from typing import Tuple, Optional, Dict, Any

from pyrogram import Client
from ..config import settings

logger = logging.getLogger(__name__)


class SessionGenerator:
    """SESSION 自动生成器"""
    
    def __init__(self):
        self.pending_logins: Dict[int, Dict[str, Any]] = {}
    
    async def send_verification_code(self, phone_number: str) -> Tuple[bool, str]:
        """发送验证码到手机号"""
        try:
            client = Client(
                name=f"temp_session",
                api_hash=settings.API_HASH,
                api_id=settings.API_ID,
                app_version="TG-Content-Bot-Pro",
                device_model="Bot",
                system_version="Linux",
                lang_code="zh",
                in_memory=True
            )
            
            await client.connect()
            
            result = await client.send_code(phone_number)
            
            self.pending_logins[phone_number] = {
                "client": client,
                "phone_code_hash": result.phone_code_hash,
                "phone_number": phone_number
            }
            
            logger.info(f"验证码已发送到 {phone_number[:7]}***")
            return True, "请回复收到的验证码（如 12345）"
            
        except Exception as e:
            logger.error(f"发送验证码失败: {e}")
            return False, f"发送失败: {str(e)}"
    
    async def verify_and_get_session(self, phone_number: str, code: str) -> Tuple[bool, str]:
        """验证验证码并获取 session"""
        if phone_number not in self.pending_logins:
            return False, "请先发送手机号"
        
        info = self.pending_logins[phone_number]
        client = info["client"]
        
        try:
            session = await client.sign_in(
                phone_number,
                info["phone_code_hash"],
                code
            )
            
            session_string = client.export_session_string()
            
            await client.disconnect()
            del self.pending_logins[phone_number]
            
            return True, session_string
            
        except Exception as e:
            logger.error(f"验证失败: {e}")
            try:
                await client.disconnect()
            except:
                pass
            if phone_number in self.pending_logins:
                del self.pending_logins[phone_number]
            return False, f"验证码错误，请重试"


session_generator = SessionGenerator()


async def generate_session_by_phone(phone_number: str) -> Tuple[bool, str]:
    """通过手机号生成 SESSION - 第一步"""
    return await session_generator.send_verification_code(phone_number)


async def verify_phone_code(phone_number: str, code: str) -> Tuple[bool, str]:
    """验证验证码并获取 session - 第二步"""
    return await session_generator.verify_and_get_session(phone_number, code)