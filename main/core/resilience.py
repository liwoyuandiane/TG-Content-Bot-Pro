"""Telegram 客户端韧性保护模块

针对 Pyrogram 在遇到 PERSISTENT_TIMESTAMP_OUTDATED 等 Telegram 500 内部错误时
陷入 0.5s x 10 次快速重试风暴、最终导致连接假死(进程存活但不再处理任何消息)
的问题,提供:

1. handle_updates 包装:捕获致命错误,指数退避 sleep + 自动重启客户端重建连接与 state
2. 兜底捕获其它未处理异常,避免 asyncio task 静默死亡导致 update 流中断

用法:
    from .resilience import install_client_resilience
    guard = install_client_resilience(client)
    # guard.stats 可查看连续错误次数、当前退避、上次重启时间
"""
import asyncio
import logging
import time
from typing import Any

from pyrogram.errors import BadRequest, InternalServerError
from pyrogram.errors import PersistentTimestampOutdated

logger = logging.getLogger(__name__)


class ClientResilienceGuard:
    """客户端韧性守护

    包装 Pyrogram Client.handle_updates:
    - 捕获 PersistentTimestampOutdated(Telegram 500,频道增量同步失败,
      由 updates.GetChannelDifference 触发,通常意味着本地 persistent state 与服务器不同步)
    - 记录错误,按指数退避 sleep,然后重启客户端重建连接与 state
    - 顺带捕获其它未处理异常,避免 asyncio task 异常泄漏
    """

    def __init__(
        self,
        client: Any,
        initial_backoff: int = 30,
        max_backoff: int = 300,
        restart_cooldown: int = 120,
        reset_after: int = 600,
    ) -> None:
        self.client = client
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.restart_cooldown = restart_cooldown
        self.reset_after = reset_after

        self._backoff = initial_backoff
        self._last_restart = 0.0
        self._restarting = False
        self._consecutive_errors = 0
        self._last_error_time = 0.0
        self._recover_lock = asyncio.Lock()
        self._original_handle_updates = client.handle_updates

    def install(self) -> "ClientResilienceGuard":
        """把守护包装安装到客户端实例上

        注意:Pyrogram 的 session 通过实例属性访问 handle_updates
        (self.client.handle_updates(msg.body)),因此把实例属性替换为
        包装函数即可生效,无需修改第三方库。
        """
        guard = self

        async def guarded_handle_updates(updates: Any) -> Any:
            try:
                return await guard._original_handle_updates(updates)
            except PersistentTimestampOutdated as e:
                await guard._recover(f"Telegram PERSISTENT_TIMESTAMP_OUTDATED: {e}")
            except InternalServerError as e:
                # 服务器内部错误(500):可能是临时性故障,退避后恢复
                await guard._recover(f"Telegram 服务器内部错误: {e}")
            except BadRequest as e:
                # 单条 update 请求无效(如 Peer id invalid / ChannelPrivate 等):
                # 只是这一条更新失败,不中断 update 流,仅记录日志
                logger.warning(
                    f"handle_updates 跳过无效更新(非致命): {type(e).__name__}: {e}"
                )
            except ValueError as e:  # Peer id invalid 等可预期错误
                # 这类错误通常是因为访问了未加入的频道或已删除的频道
                # 记录为警告，避免刷屏并且不影响后续更新处理
                logger.warning(f"忽略无效的 Peer id: {e}")
            except Exception as e:  # noqa: BLE001 - 兜底所有未捕获异常
                # 未知异常:保守起见记录日志,不重启(避免误伤正常连接)
                logger.error(f"handle_updates 未捕获异常: {e}", exc_info=True)
            return None

        self.client.handle_updates = guarded_handle_updates
        logger.info("✅ 客户端韧性保护已安装 (handle_updates guard)")
        return self

    async def _recover(self, reason: str) -> None:
        """致命错误恢复:退避 sleep + 重启客户端

        使用锁保证并发触发时退避计数与重启调度串行执行。
        """
        # 串行化恢复流程, 避免多个 update task 并发时重复计数/重启
        async with self._recover_lock:
            now = time.monotonic()
            self._consecutive_errors += 1

            # 错误安静一段时间后,重置退避状态(说明问题已恢复)
            if self._last_error_time and (now - self._last_error_time) >= self.reset_after:
                self._consecutive_errors = 1
                self._backoff = self.initial_backoff
            self._last_error_time = now

            # 指数退避:连续错误次数越多等待越久,封顶 max_backoff
            delay = min(self.initial_backoff * (2 ** (self._consecutive_errors - 1)), self.max_backoff)
            self._backoff = delay
            logger.error(
                f"🔴 检测到客户端致命错误(连续 {self._consecutive_errors} 次): {reason}"
            )
            logger.error(f"⏳ 等待 {delay} 秒后再重建客户端连接...")

            if self._restarting:
                logger.info("已有重启在进行中,跳过本次重启")
                return
            if now - self._last_restart < self.restart_cooldown:
                logger.info(
                    f"距离上次重启不足 {self.restart_cooldown}s,跳过本次重启"
                )
                return

            self._restarting = True
            try:
                # 在独立 task 中执行 stop+start,避免阻塞当前 update 处理
                self.client.loop.create_task(self._do_restart())
            except Exception as e:  # noqa: BLE001
                logger.error(f"调度客户端重启失败: {e}", exc_info=True)
                self._restarting = False

            # 在锁内等待退避, 保证并发触发者不会重复计数
            await asyncio.sleep(delay)

    async def _do_restart(self) -> None:
        """执行 stop + start 重启流程,完成后更新状态"""
        try:
            if self.client.is_connected:
                logger.info("  → 停止客户端...")
                await self.client.stop()
            logger.info("  → 启动客户端...")
            await self.client.start()
            self._last_restart = time.monotonic()
            # 注意:不在此重置退避/错误计数。退避只在错误安静
            # reset_after 秒后由 _recover 重置,避免错误持续时形成重启风暴
            logger.info("✅ 客户端重启完成,连接已重建")
        except Exception as e:  # noqa: BLE001
            logger.error(f"❌ 客户端重启失败: {e}", exc_info=True)
        finally:
            self._restarting = False

    @property
    def stats(self) -> dict:
        """当前守护状态"""
        return {
            "consecutive_errors": self._consecutive_errors,
            "current_backoff": self._backoff,
            "last_restart": self._last_restart,
            "restarting": self._restarting,
        }


def install_client_resilience(client: Any) -> ClientResilienceGuard:
    """安装客户端韧性保护,返回 guard 实例

    Args:
        client: Pyrogram Client 实例(bot 或 userbot)

    Returns:
        ClientResilienceGuard: 已安装的守护实例,可查看 stats
    """
    return ClientResilienceGuard(client).install()
