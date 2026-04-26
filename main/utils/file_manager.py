"""文件管理器模块"""
import os
import tempfile
import logging
import shutil
from typing import Optional, Union
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)


class FileManager:
    """文件管理器"""
    
    def __init__(self, base_temp_dir: str = "temp"):
        self.base_temp_dir = base_temp_dir
        self._ensure_temp_dir()
    
    def _ensure_temp_dir(self):
        """确保临时目录存在"""
        if not os.path.exists(self.base_temp_dir):
            os.makedirs(self.base_temp_dir)
            logger.info(f"创建临时目录: {self.base_temp_dir}")
    
    @contextmanager
    def temporary_file(self, suffix: str = "", prefix: str = "tmp_"):
        """创建临时文件的上下文管理器"""
        temp_file = None
        try:
            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(
                suffix=suffix,
                prefix=prefix,
                dir=self.base_temp_dir,
                delete=False
            )
            temp_file.close()  # 关闭文件以便其他代码可以使用
            
            logger.debug(f"创建临时文件: {temp_file.name}")
            yield temp_file.name
        except Exception as e:
            logger.error(f"临时文件操作出错: {e}")
            raise
        finally:
            # 清理临时文件
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.remove(temp_file.name)
                    logger.debug(f"清理临时文件: {temp_file.name}")
                except Exception as e:
                    logger.warning(f"清理临时文件失败 {temp_file.name}: {e}")
    
    @contextmanager
    def temporary_directory(self, prefix: str = "tmp_dir_"):
        """创建临时目录的上下文管理器"""
        temp_dir = None
        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp(
                prefix=prefix,
                dir=self.base_temp_dir
            )
            
            logger.debug(f"创建临时目录: {temp_dir}")
            yield temp_dir
        except Exception as e:
            logger.error(f"临时目录操作出错: {e}")
            raise
        finally:
            # 清理临时目录
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logger.debug(f"清理临时目录: {temp_dir}")
                except Exception as e:
                    logger.warning(f"清理临时目录失败 {temp_dir}: {e}")
    
    def cleanup_temp_files(self):
        """清理所有临时文件"""
        try:
            if os.path.exists(self.base_temp_dir):
                shutil.rmtree(self.base_temp_dir)
                logger.info(f"清理所有临时文件: {self.base_temp_dir}")
                self._ensure_temp_dir()
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")
    
    def get_file_size(self, file_path: str) -> int:
        """获取文件大小"""
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"获取文件大小失败 {file_path}: {e}")
            return 0
    
    def file_exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
        return os.path.exists(file_path) and os.path.isfile(file_path)
    
    def move_file(self, src: str, dst: str) -> bool:
        """移动文件"""
        try:
            shutil.move(src, dst)
            logger.debug(f"移动文件: {src} -> {dst}")
            return True
        except Exception as e:
            logger.error(f"移动文件失败 {src} -> {dst}: {e}")
            return False
    
    def copy_file(self, src: str, dst: str) -> bool:
        """复制文件"""
        try:
            shutil.copy2(src, dst)
            logger.debug(f"复制文件: {src} -> {dst}")
            return True
        except Exception as e:
            logger.error(f"复制文件失败 {src} -> {dst}: {e}")
            return False
    
    def safe_remove(self, file_path: str) -> bool:
        """安全删除文件"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"删除文件: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"删除文件失败 {file_path}: {e}")
            return False
    
    def rename_file(self, src: str, dst: str) -> bool:
        """重命名文件
        
        Args:
            src: 源文件路径
            dst: 目标文件路径
            
        Returns:
            操作成功返回 True，失败返回 False
        """
        try:
            if not os.path.exists(src):
                logger.error(f"源文件不存在: {src}")
                return False
            
            os.rename(src, dst)
            logger.debug(f"重命名文件: {src} -> {dst}")
            return True
        except Exception as e:
            logger.error(f"重命名文件失败 {src} -> {dst}: {e}")
            return False
    
    def get_file_extension(self, file_path: str) -> str:
        """获取文件扩展名
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件扩展名（不含点）
        """
        return os.path.splitext(file_path)[1].lstrip('.').lower()
    
    def get_file_name(self, file_path: str) -> str:
        """获取文件名（不含路径）
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件名
        """
        return os.path.basename(file_path)
    
    def get_file_name_without_extension(self, file_path: str) -> str:
        """获取文件名（不含路径和扩展名）
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件名（不含扩展名）
        """
        return os.path.splitext(os.path.basename(file_path))[0]
    
    def create_directory(self, dir_path: str) -> bool:
        """创建目录（包括父目录）
        
        Args:
            dir_path: 目录路径
            
        Returns:
            操作成功返回 True，失败返回 False
        """
        try:
            os.makedirs(dir_path, exist_ok=True)
            logger.debug(f"创建目录: {dir_path}")
            return True
        except Exception as e:
            logger.error(f"创建目录失败 {dir_path}: {e}")
            return False
    
    def get_directory_size(self, dir_path: str) -> int:
        """获取目录大小
        
        Args:
            dir_path: 目录路径
            
        Returns:
            目录大小（字节）
        """
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(dir_path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    if os.path.isfile(file_path):
                        total_size += os.path.getsize(file_path)
            return total_size
        except Exception as e:
            logger.error(f"获取目录大小失败 {dir_path}: {e}")
            return 0
    
    def split_file(self, file_path: str, chunk_size: int = 1900 * 1024 * 1024) -> list:
        """将大文件分割成多个小块
        
        Args:
            file_path: 要分割的文件路径
            chunk_size: 每个块的大小（默认1.9GB，适合Telegram上传限制）
            
        Returns:
            分割后的文件列表
        """
        try:
            file_size = self.get_file_size(file_path)
            if file_size <= chunk_size:
                return [file_path]
            
            chunks = []
            base_name, ext = os.path.splitext(file_path)
            chunk_count = (file_size + chunk_size - 1) // chunk_size
            
            logger.info(f"开始分割文件: {file_path}, 总大小: {file_size}, 分成: {chunk_count} 块")
            
            # 创建临时目录存放分片
            temp_dir = tempfile.mkdtemp(prefix="split_", dir=self.base_temp_dir)
            
            with open(file_path, 'rb') as f:
                for i in range(chunk_count):
                    chunk_file = os.path.join(temp_dir, f"{base_name}.part{i+1:03d}{ext}")
                    with open(chunk_file, 'wb') as chunk_f:
                        chunk = f.read(chunk_size)
                        chunk_f.write(chunk)
                    chunks.append(chunk_file)
                    logger.debug(f"已创建分片: {chunk_file}")
            
            logger.info(f"文件分割完成，生成 {len(chunks)} 个分片")
            return chunks
        except Exception as e:
            logger.error(f"分割文件失败 {file_path}: {e}")
            return [file_path]


# 全局文件管理器实例
file_manager = FileManager()


@contextmanager
def managed_temp_file(suffix: str = "", prefix: str = "tmp_"):
    """临时文件上下文管理器"""
    with file_manager.temporary_file(suffix, prefix) as temp_file:
        yield temp_file


@contextmanager
def managed_temp_directory(prefix: str = "tmp_dir_"):
    """临时目录上下文管理器"""
    with file_manager.temporary_directory(prefix) as temp_dir:
        yield temp_dir