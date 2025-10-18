"""媒体工具模块"""
import asyncio
import re
import os
import time
import math
from datetime import datetime as dt
from typing import Optional
from pyrogram.errors import FloodWait, InviteHashInvalid, InviteHashExpired, UserAlreadyParticipant

from ..exceptions.telegram import SessionException
from .file_manager import file_manager

def hhmmss(seconds: int) -> str:
    """将秒数转换为HH:MM:SS格式"""
    return time.strftime('%H:%M:%S', time.gmtime(seconds))


async def screenshot(video: str, duration: int, sender: int) -> Optional[str]:
    """为视频生成缩略图"""
    # 检查用户特定的缩略图
    user_thumb = f'{sender}.jpg'
    if file_manager.file_exists(user_thumb):
        return user_thumb
    
    time_stamp = hhmmss(int(duration) // 2)
    out = dt.now().isoformat("_", "seconds") + ".jpg"
    
    cmd = [
        "ffmpeg",
        "-ss",
        f"{time_stamp}", 
        "-i",
        f"{video}",
        "-frames:v",
        "1", 
        f"{out}",
        "-y"
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if file_manager.file_exists(out):
            return out
        else:
            return None
    except Exception as e:
        print(f"生成缩略图失败: {e}")
        return None


async def progress_for_pyrogram(current: int, total: int, client, ud_type: str, message, start: float):
    """Pyrogram下载/上传进度回调"""
    now = time.time()
    diff = now - start
    if round(diff % 10.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000
        estimated_total_time = elapsed_time + time_to_completion

        elapsed_time = TimeFormatter(milliseconds=elapsed_time)
        estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)

        progress = "[{0}{1}] \nP: {2}%\n".format(
            ''.join(["█" for i in range(math.floor(percentage / 5))]),
            ''.join(["░" for i in range(20 - math.floor(percentage / 5))]),
            round(percentage, 2))

        tmp = progress + "{0} of {1}\nSpeed: {2}/s\nETA: {3}\n".format(
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),
            estimated_total_time if estimated_total_time != '' else "0 s"
        )
        try:
            await message.edit(
                text="{}\n {}".format(
                    ud_type,
                    tmp
                )
            )
        except:
            pass


def humanbytes(size: int) -> str:
    """将字节数转换为人类可读格式"""
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'


def TimeFormatter(milliseconds: int) -> str:
    """将毫秒转换为时间格式"""
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "") + \
        ((str(milliseconds) + "ms, ") if milliseconds else "")
    return tmp[:-2]


def get_link(string: str) -> Optional[str]:
    """从字符串中提取链接"""
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    url = re.findall(regex, string)   
    try:
        link = [x[0] for x in url][0]
        if link:
            return link
        else:
            return None
    except Exception:
        return None


async def join_chat(client, invite_link: str) -> str:
    """加入私有聊天"""
    if client is None:
        raise SessionException("未配置 SESSION，无法加入频道")
    
    try:
        await client.join_chat(invite_link)
        return "✅ 成功加入频道"
    except UserAlreadyParticipant:
        return "✅ 您已经是该频道的成员"
    except (InviteHashInvalid, InviteHashExpired):
        return "❌ 无法加入，邀请链接已过期或无效"
    except FloodWait as e:
        return f"❌ 请求过多，请等待 {e.value} 秒后重试"
    except Exception as e:
        print(f"加入频道时出错: {e}")
        return "❌ 无法加入，请尝试手动加入"