"""SESSION工具模块"""

import base64
import struct
import logging

logger = logging.getLogger(__name__)


def validate_pyrogram_session(session_string: str) -> bool:
    """
    验证Pyrogram SESSION字符串格式
    
    Args:
        session_string: Pyrogram SESSION字符串
        
    Returns:
        bool: SESSION格式是否有效
    """
    if not session_string:
        return False
    
    try:
        # 尝试解码SESSION字符串
        padded_session = session_string + "=" * (-len(session_string) % 4)
        decoded_data = base64.urlsafe_b64decode(padded_session)
        
        # 尝试按照Pyrogram v2格式解包
        # 格式: >BI?256sQ?
        # B: dc_id (1字节)
        # I: api_id (4字节)
        # ?: test_mode (1字节)
        # 256s: auth_key (256字节)
        # Q: user_id (8字节)
        # ?: is_bot (1字节)
        # 总计: 1+4+1+256+8+1 = 271字节
        if len(decoded_data) >= 271:
            struct.unpack(">BI?256sQ?", decoded_data[:271])
            return True
        else:
            logger.warning(f"SESSION数据长度不足: {len(decoded_data)} 字节，需要至少271字节")
            return False
    except Exception as e:
        logger.warning(f"SESSION验证失败: {e}")
        return False


def sanitize_pyrogram_session(session_string: str) -> str:
    """
    清理Pyrogram SESSION字符串
    
    Args:
        session_string: 原始SESSION字符串
        
    Returns:
        str: 清理后的SESSION字符串
    """
    if not session_string:
        return session_string
    
    # 只移除首尾空格，不移除其他字符
    cleaned = session_string.strip()
    
    # 验证清理后的SESSION
    if validate_pyrogram_session(cleaned):
        logger.info(f"SESSION清理完成，长度: {len(cleaned)}")
        return cleaned
    else:
        logger.warning("清理后的SESSION格式可能无效")
        return cleaned


def get_session_info(session_string: str) -> dict:
    """
    获取SESSION信息（不包含敏感数据）
    
    Args:
        session_string: SESSION字符串
        
    Returns:
        dict: SESSION信息
    """
    if not session_string:
        return {}
    
    try:
        padded_session = session_string + "=" * (-len(session_string) % 4)
        decoded_data = base64.urlsafe_b64decode(padded_session)
        
        if len(decoded_data) >= 271:
            dc_id, api_id, test_mode, _, user_id, is_bot = struct.unpack(">BI?256sQ?", decoded_data[:271])
            return {
                "dc_id": dc_id,
                "api_id": api_id,
                "test_mode": test_mode,
                "user_id": user_id,
                "is_bot": is_bot,
                "length": len(session_string),
                "valid": True
            }
    except Exception as e:
        logger.error(f"解析SESSION信息失败: {e}")
    
    return {
        "length": len(session_string),
        "valid": validate_pyrogram_session(session_string)
    }