"""文件缓存模块

提供文件缓存功能，减少重复的文件操作，提升性能。
"""
import os
import time
import hashlib
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class FileCache:
    """文件缓存管理器"""
    
    def __init__(self, cache_dir: str = "cache", max_size: int = 100, ttl: int = 3600):
        """初始化文件缓存
        
        Args:
            cache_dir: 缓存目录
            max_size: 最大缓存文件数
            ttl: 缓存生存时间（秒）
        """
        self.cache_dir = Path(cache_dir)
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        # 确保缓存目录存在
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载现有缓存索引
        self._load_cache_index()
    
    def _get_cache_key(self, content: str) -> str:
        """生成缓存键
        
        Args:
            content: 内容字符串
            
        Returns:
            str: 缓存键
        """
        return hashlib.md5(content.encode()).hexdigest()
    
    def _load_cache_index(self):
        """加载缓存索引"""
        try:
            index_file = self.cache_dir / "index.txt"
            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        key, timestamp, size = line.strip().split('|')
                        self._cache[key] = {
                            'timestamp': float(timestamp),
                            'size': int(size)
                        }
        except Exception as e:
            logger.warning(f"加载缓存索引失败: {e}")
    
    def _save_cache_index(self):
        """保存缓存索引"""
        try:
            index_file = self.cache_dir / "index.txt"
            with open(index_file, 'w', encoding='utf-8') as f:
                for key, info in self._cache.items():
                    f.write(f"{key}|{info['timestamp']}|{info['size']}\n")
        except Exception as e:
            logger.warning(f"保存缓存索引失败: {e}")
    
    def _clean_expired_cache(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = []
        
        for key, info in self._cache.items():
            if current_time - info['timestamp'] > self.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            self._remove_cache_file(key)
            del self._cache[key]
        
        # 如果缓存仍然过大，清理最旧的缓存
        if len(self._cache) > self.max_size:
            sorted_keys = sorted(self._cache.keys(), 
                               key=lambda k: self._cache[k]['timestamp'])
            keys_to_remove = sorted_keys[:len(self._cache) - self.max_size]
            
            for key in keys_to_remove:
                self._remove_cache_file(key)
                del self._cache[key]
    
    def _remove_cache_file(self, key: str):
        """移除缓存文件
        
        Args:
            key: 缓存键
        """
        try:
            cache_file = self.cache_dir / f"{key}.cache"
            if cache_file.exists():
                cache_file.unlink()
        except Exception as e:
            logger.warning(f"移除缓存文件失败 {key}: {e}")
    
    def get(self, content: str) -> Optional[str]:
        """获取缓存内容
        
        Args:
            content: 内容字符串
            
        Returns:
            Optional[str]: 缓存文件路径，如果不存在则返回None
        """
        key = self._get_cache_key(content)
        
        if key not in self._cache:
            return None
        
        # 检查缓存是否过期
        if time.time() - self._cache[key]['timestamp'] > self.ttl:
            self._remove_cache_file(key)
            del self._cache[key]
            return None
        
        cache_file = self.cache_dir / f"{key}.cache"
        if not cache_file.exists():
            del self._cache[key]
            return None
        
        # 更新访问时间
        self._cache[key]['timestamp'] = time.time()
        self._save_cache_index()
        
        return str(cache_file)
    
    def put(self, content: str, file_path: str) -> str:
        """添加缓存
        
        Args:
            content: 内容字符串
            file_path: 文件路径
            
        Returns:
            str: 缓存文件路径
        """
        # 清理过期缓存
        self._clean_expired_cache()
        
        key = self._get_cache_key(content)
        cache_file = self.cache_dir / f"{key}.cache"
        
        try:
            # 复制文件到缓存目录
            import shutil
            shutil.copy2(file_path, cache_file)
            
            # 更新缓存索引
            self._cache[key] = {
                'timestamp': time.time(),
                'size': os.path.getsize(cache_file)
            }
            
            self._save_cache_index()
            
            return str(cache_file)
            
        except Exception as e:
            logger.error(f"添加缓存失败: {e}")
            return file_path
    
    def clear(self):
        """清空缓存"""
        try:
            # 删除所有缓存文件
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink()
            
            # 删除索引文件
            index_file = self.cache_dir / "index.txt"
            if index_file.exists():
                index_file.unlink()
            
            self._cache.clear()
            logger.info("缓存已清空")
            
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")


# 全局文件缓存实例
file_cache = FileCache()