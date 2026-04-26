"""流式文件处理模块"""
import os
import asyncio
import logging
from typing import AsyncGenerator, Optional
from .file_manager import file_manager

logger = logging.getLogger(__name__)


class StreamProcessor:
    """流式文件处理器"""
    
    def __init__(self, chunk_size: int = 1024 * 1024):  # 默认1MB块大小
        self.chunk_size = chunk_size
    
    async def stream_file(self, file_path: str) -> AsyncGenerator[bytes, None]:
        """流式读取文件"""
        try:
            file_size = file_manager.get_file_size(file_path)
            logger.debug(f"开始流式传输文件: {file_path} ({file_size} bytes)")
            
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                    yield chunk
                    
            logger.debug(f"文件流式传输完成: {file_path}")
        except Exception as e:
            logger.error(f"流式传输文件失败 {file_path}: {e}")
            raise
    
    async def write_stream_to_file(self, stream: AsyncGenerator[bytes, None], 
                                 output_path: str) -> int:
        """将流写入文件"""
        try:
            total_bytes = 0
            with open(output_path, 'wb') as f:
                async for chunk in stream:
                    f.write(chunk)
                    total_bytes += len(chunk)
                    
            logger.debug(f"流写入完成: {output_path} ({total_bytes} bytes)")
            return total_bytes
        except Exception as e:
            logger.error(f"流写入文件失败 {output_path}: {e}")
            raise
    
    async def copy_file_streaming(self, src: str, dst: str) -> int:
        """流式复制文件"""
        try:
            # 使用流式传输复制文件
            async def file_stream():
                async for chunk in self.stream_file(src):
                    yield chunk
            
            bytes_copied = await self.write_stream_to_file(file_stream(), dst)
            logger.debug(f"流式复制完成: {src} -> {dst} ({bytes_copied} bytes)")
            return bytes_copied
        except Exception as e:
            logger.error(f"流式复制文件失败 {src} -> {dst}: {e}")
            raise


# 全局流处理器实例
stream_processor = StreamProcessor()


async def stream_file(file_path: str, chunk_size: int = 1024 * 1024) -> AsyncGenerator[bytes, None]:
    """流式读取文件的便捷函数"""
    processor = StreamProcessor(chunk_size)
    async for chunk in processor.stream_file(file_path):
        yield chunk


async def copy_file_with_streaming(src: str, dst: str, chunk_size: int = 1024 * 1024) -> int:
    """流式复制文件的便捷函数"""
    processor = StreamProcessor(chunk_size)
    return await processor.copy_file_streaming(src, dst)