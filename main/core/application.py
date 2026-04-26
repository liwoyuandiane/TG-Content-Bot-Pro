"""应用架构核心模块

提供现代化的应用架构，包括依赖注入、模块化管理和生命周期管理。
"""
import asyncio
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from ..utils.logging_config import get_logger
from ..utils.error_handler import safe_execute
from ..utils.performance_monitor import performance_monitor

logger = get_logger(__name__)


class ServiceState(Enum):
    """服务状态枚举"""
    CREATED = "created"
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ServiceInfo:
    """服务信息"""
    name: str
    service: Any
    state: ServiceState
    dependencies: List[str]
    priority: int  # 启动优先级，数字越小优先级越高


class Service(ABC):
    """服务基类"""
    
    def __init__(self, name: str, dependencies: Optional[List[str]] = None, priority: int = 10):
        self.name = name
        self.dependencies = dependencies or []
        self.priority = priority
        self.state = ServiceState.CREATED
        self.logger = get_logger(f"service.{name}")
    
    @abstractmethod
    async def initialize(self) -> None:
        """初始化服务"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """关闭服务"""
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "name": self.name,
            "state": self.state.value,
            "healthy": self.state == ServiceState.RUNNING
        }


class Application:
    """应用核心类"""
    
    def __init__(self, name: str = "TG-Content-Bot-Pro"):
        self.name = name
        self.services: Dict[str, ServiceInfo] = {}
        self.state = ServiceState.CREATED
        self.logger = get_logger(__name__)
        self._startup_time: Optional[float] = None
        self._shutdown_time: Optional[float] = None
    
    def register_service(self, service: Service) -> None:
        """注册服务
        
        Args:
            service: 服务实例
        """
        if service.name in self.services:
            raise ValueError(f"服务 '{service.name}' 已注册")
        
        service_info = ServiceInfo(
            name=service.name,
            service=service,
            state=ServiceState.CREATED,
            dependencies=service.dependencies,
            priority=service.priority
        )
        
        self.services[service.name] = service_info
        self.logger.info("注册服务: %s (优先级: %d)", service.name, service.priority)
    
    def get_service(self, name: str) -> Optional[Service]:
        """获取服务
        
        Args:
            name: 服务名称
            
        Returns:
            服务实例，如果不存在则返回None
        """
        service_info = self.services.get(name)
        return service_info.service if service_info else None
    
    async def start(self) -> None:
        """启动应用，初始化所有服务"""
        self.state = ServiceState.INITIALIZING
        self._startup_time = asyncio.get_event_loop().time()
        
        self.logger.info("开始初始化 %d 个服务", len(self.services))
        
        # 按优先级排序服务
        sorted_services = sorted(
            self.services.values(),
            key=lambda s: s.priority
        )
        
        initialized_count = 0
        
        for service_info in sorted_services:
            try:
                await self._initialize_service(service_info)
                initialized_count += 1
            except Exception as e:
                self.logger.error("服务 %s 初始化失败: %s", service_info.name, e)
                service_info.state = ServiceState.ERROR
                # 关键服务失败则停止启动流程
                if service_info.priority <= 5:  # 高优先级服务
                    raise
        
        self.state = ServiceState.RUNNING
        startup_duration = asyncio.get_event_loop().time() - self._startup_time
        
        self.logger.info(
            "应用启动完成，成功初始化 %d/%d 个服务，耗时 %.2f 秒",
            initialized_count, len(self.services), startup_duration
        )
    
    async def _initialize_service(self, service_info: ServiceInfo) -> None:
        """初始化单个服务"""
        # 检查依赖服务是否就绪
        for dep_name in service_info.dependencies:
            dep_info = self.services.get(dep_name)
            if not dep_info or dep_info.state != ServiceState.RUNNING:
                raise RuntimeError(f"依赖服务 '{dep_name}' 未就绪")
        
        service_info.state = ServiceState.INITIALIZING
        self.logger.info("初始化服务: %s", service_info.name)
        
        # 使用性能监控初始化服务
        with performance_monitor.measure(f"initialize_{service_info.name}") as record:
            await service_info.service.initialize()
        
        service_info.state = ServiceState.RUNNING
        
        if record and record.duration:
            self.logger.info(
                "服务 %s 初始化完成，耗时 %.2f ms",
                service_info.name, record.duration
            )
    
    async def stop(self) -> None:
        """停止应用，关闭所有服务"""
        if self.state in [ServiceState.STOPPING, ServiceState.STOPPED]:
            return
        
        self.state = ServiceState.STOPPING
        self._shutdown_time = asyncio.get_event_loop().time()
        
        self.logger.info("开始关闭 %d 个服务", len(self.services))
        
        # 按优先级逆序关闭服务
        sorted_services = sorted(
            self.services.values(),
            key=lambda s: s.priority,
            reverse=True
        )
        
        shutdown_count = 0
        
        for service_info in sorted_services:
            if service_info.state == ServiceState.RUNNING:
                try:
                    await self._shutdown_service(service_info)
                    shutdown_count += 1
                except Exception as e:
                    self.logger.error("服务 %s 关闭失败: %s", service_info.name, e)
        
        self.state = ServiceState.STOPPED
        shutdown_duration = asyncio.get_event_loop().time() - self._shutdown_time
        
        self.logger.info(
            "应用关闭完成，成功关闭 %d/%d 个服务，耗时 %.2f 秒",
            shutdown_count, len(self.services), shutdown_duration
        )
    
    async def _shutdown_service(self, service_info: ServiceInfo) -> None:
        """关闭单个服务"""
        service_info.state = ServiceState.STOPPING
        self.logger.info("关闭服务: %s", service_info.name)
        
        # 使用安全执行关闭服务
        await safe_execute(
            service_info.service.shutdown(),
            default_return=None,
            log_error=True
        )
        
        service_info.state = ServiceState.STOPPED
        self.logger.info("服务 %s 已关闭", service_info.name)
    
    async def health_check(self) -> Dict[str, Any]:
        """应用健康检查"""
        services_health = {}
        healthy_count = 0
        total_count = len(self.services)
        
        for service_info in self.services.values():
            health_data = await service_info.service.health_check()
            services_health[service_info.name] = health_data
            
            if health_data["healthy"]:
                healthy_count += 1
        
        return {
            "name": self.name,
            "state": self.state.value,
            "uptime": asyncio.get_event_loop().time() - self._startup_time if self._startup_time else 0,
            "services": {
                "total": total_count,
                "healthy": healthy_count,
                "unhealthy": total_count - healthy_count
            },
            "services_health": services_health
        }


class ConfigService(Service):
    """配置服务"""
    
    def __init__(self):
        super().__init__("config", priority=1)  # 最高优先级
    
    async def initialize(self) -> None:
        """初始化配置服务"""
        from ..config import settings
        from ..utils.config_validator import ensure_config_integrity
        
        self.logger.info("验证配置完整性")
        
        if not ensure_config_integrity():
            raise RuntimeError("配置验证失败")
        
        self.logger.info("配置验证通过")
        
        # 记录配置摘要（不包含敏感信息）
        safe_config = settings.get_safe_summary()
        self.logger.debug("配置摘要: %s", safe_config)
    
    async def shutdown(self) -> None:
        """关闭配置服务"""
        self.logger.info("配置服务关闭")


class DatabaseService(Service):
    """数据库服务"""
    
    def __init__(self):
        super().__init__("database", dependencies=["config"], priority=2)
    
    async def initialize(self) -> None:
        """初始化数据库服务"""
        from .database import db_manager
        
        self.logger.info("初始化数据库连接")
        
        # 初始化数据库连接
        await db_manager.initialize()
        
        self.logger.info("数据库服务初始化完成")
    
    async def shutdown(self) -> None:
        """关闭数据库服务"""
        from .database import db_manager
        
        self.logger.info("关闭数据库连接")
        
        # 关闭数据库连接
        await db_manager.close()
        
        self.logger.info("数据库服务已关闭")


class ClientService(Service):
    """客户端服务"""
    
    def __init__(self):
        super().__init__("clients", dependencies=["config"], priority=3)
    
    async def initialize(self) -> None:
        """初始化客户端服务"""
        from .clients import client_manager
        
        self.logger.info("初始化Telegram客户端")
        
        await client_manager.initialize_clients()
        
        self.logger.info("客户端服务初始化完成")
    
    async def shutdown(self) -> None:
        """关闭客户端服务"""
        from .clients import client_manager
        
        self.logger.info("关闭Telegram客户端")
        
        await client_manager.stop_clients()
        
        self.logger.info("客户端服务已关闭")


class PluginService(Service):
    """插件服务"""
    
    def __init__(self):
        super().__init__("plugins", dependencies=["clients", "database"], priority=4)
    
    async def initialize(self) -> None:
        """初始化插件服务"""
        from .plugin_manager import plugin_manager
        from .base_plugin import plugin_registry
        
        self.logger.info("加载插件")
        
        # 加载所有插件
        results = plugin_manager.load_all_plugins()
        loaded_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        self.logger.info("插件加载完成: %d/%d", loaded_count, total_count)
        
        # 注册插件事件处理器
        await plugin_registry.load_all_plugins()
        
        self.logger.info("插件服务初始化完成")
    
    async def shutdown(self) -> None:
        """关闭插件服务"""
        self.logger.info("插件服务关闭")


class TaskQueueService(Service):
    """任务队列服务"""
    
    def __init__(self):
        super().__init__("task_queue", dependencies=["config"], priority=5)
    
    async def initialize(self) -> None:
        """初始化任务队列服务"""
        # 已移除下载功能，跳过任务队列初始化
        self.logger.info("ℹ️ 已移除下载功能，跳过任务队列初始化")
    
    async def shutdown(self) -> None:
        """关闭任务队列服务"""
        # 已移除下载功能，跳过任务队列停止
        self.logger.info("ℹ️ 已移除下载功能，跳过任务队列停止")


# 创建全局应用实例
app = Application("TG-Content-Bot-Pro")


def create_default_app() -> Application:
    """创建默认应用实例
    
    Returns:
        配置好的应用实例
    """
    # 注册核心服务
    app.register_service(ConfigService())
    app.register_service(DatabaseService())
    app.register_service(ClientService())
    app.register_service(PluginService())
    app.register_service(TaskQueueService())
    
    return app