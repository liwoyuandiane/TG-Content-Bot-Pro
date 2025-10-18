"""速率限制器模块"""
import asyncio
import logging
import time
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """速率限制异常"""
    pass


class RateLimiter:
    """速率限制器，使用令牌桶算法"""
    
    def __init__(self, rate_per_second: float = 1.0, burst: int = 5):
        """
        初始化速率限制器
        
        Args:
            rate_per_second: 每秒允许的请求数
            burst: 突发允许的最大请求数
        """
        self.rate_per_second = rate_per_second
        self.burst = burst
        self.tokens = float(burst)
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()
        self._closed = False
    
    async def acquire(self, tokens: int = 1) -> None:
        """获取令牌，如果没有令牌则等待"""
        if self._closed:
            raise RateLimitError("速率限制器已关闭")
        
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            
            # 补充令牌
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate_per_second)
            self.last_update = now
            
            if self.tokens >= tokens:
                # 有足够的令牌
                self.tokens -= tokens
                return
            
            # 计算需要等待的时间
            wait_time = (tokens - self.tokens) / self.rate_per_second
            logger.debug(f"速率限制: 等待 {wait_time:.2f} 秒获取 {tokens} 个令牌")
            
            # 等待并补充令牌
            await asyncio.sleep(wait_time)
            self.tokens = max(0, self.tokens - tokens)
            self.last_update = time.monotonic()
    
    def get_available_tokens(self) -> float:
        """获取当前可用令牌数"""
        if self._closed:
            return 0.0
        
        now = time.monotonic()
        elapsed = now - self.last_update
        return min(self.burst, self.tokens + elapsed * self.rate_per_second)
    
    def update_rate(self, new_rate: float) -> None:
        """更新速率"""
        if new_rate <= 0:
            raise ValueError("速率必须大于0")
        
        async def _update_rate():
            async with self.lock:
                # 更新当前令牌数
                now = time.monotonic()
                elapsed = now - self.last_update
                self.tokens = min(self.burst, self.tokens + elapsed * self.rate_per_second)
                self.last_update = now
                
                # 更新速率
                self.rate_per_second = new_rate
        
        # 在事件循环中执行
        try:
            loop = asyncio.get_running_loop()
            asyncio.ensure_future(_update_rate(), loop=loop)
        except RuntimeError:
            # 没有运行中的事件循环
            pass
    
    def close(self) -> None:
        """关闭速率限制器"""
        self._closed = True


class AdaptiveRateLimiter(RateLimiter):
    """自适应速率限制器，根据错误动态调整"""
    
    def __init__(self, initial_rate: float = 1.0, burst: int = 5, 
                 min_rate: float = 0.1, max_rate: float = 10.0):
        super().__init__(initial_rate, burst)
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.flood_wait_count = 0
        self.success_count = 0
        self.last_rate_adjustment = time.monotonic()
        self.rate_adjustment_interval = 60.0  # 速率调整间隔（秒）
    
    async def on_flood_wait(self, wait_seconds: float) -> None:
        """收到FloodWait错误时调用"""
        if self._closed:
            return
        
        async with self.lock:
            self.flood_wait_count += 1
            
            # 降低速率（至少降低到最小速率）
            new_rate = max(self.min_rate, self.rate_per_second * 0.5)
            if new_rate != self.rate_per_second:
                self.rate_per_second = new_rate
                logger.warning(f"收到FloodWait({wait_seconds:.1f}s)，降低速率至 {self.rate_per_second:.2f}/s")
            
            # 等待指定时间
            await asyncio.sleep(wait_seconds + 1)
    
    async def on_success(self) -> None:
        """请求成功时调用"""
        if self._closed:
            return
        
        async with self.lock:
            self.success_count += 1
            
            # 检查是否需要调整速率
            now = time.monotonic()
            if (now - self.last_rate_adjustment) >= self.rate_adjustment_interval:
                await self._adjust_rate()
                self.last_rate_adjustment = now
    
    async def _adjust_rate(self) -> None:
        """调整速率"""
        if self.flood_wait_count == 0 and self.success_count >= 10:
            # 连续成功且没有FloodWait错误，提高速率
            new_rate = min(self.max_rate, self.rate_per_second * 1.2)
            if new_rate != self.rate_per_second:
                self.rate_per_second = new_rate
                logger.info(f"连续成功，提高速率至 {self.rate_per_second:.2f}/s")
        
        # 重置计数器
        self.flood_wait_count = 0
        self.success_count = 0


# 全局速率限制器实例
rate_limiter = AdaptiveRateLimiter(initial_rate=0.5, burst=3)


async def get_rate_limiter() -> AdaptiveRateLimiter:
    """获取速率限制器实例的便捷函数"""
    return rate_limiter