"""基插件类"""
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from ..core.clients import client_manager
from ..services.user_service import user_service
from ..services.session_service import session_service
from ..services.traffic_service import traffic_service
from ..services.download_service import download_service
from ..utils.logging_config import get_logger


class BasePlugin(ABC):
    """插件基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"plugin.{name}")
        
        # 注入核心服务
        self.clients = client_manager
        self.users = user_service
        self.sessions = session_service
        self.traffic = traffic_service
        self.downloads = download_service
    
    @abstractmethod
    async def on_load(self):
        """插件加载时调用"""
        pass
    
    @abstractmethod
    async def on_unload(self):
        """插件卸载时调用"""
        pass
    
    async def on_start(self):
        """应用启动时调用"""
        pass
    
    async def on_stop(self):
        """应用停止时调用"""
        pass
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取插件配置"""
        # 这里可以实现插件特定的配置管理
        return default
    
    def set_config(self, key: str, value: Any):
        """设置插件配置"""
        # 这里可以实现插件特定的配置管理
        pass


class PluginRegistry:
    """插件注册表"""
    
    def __init__(self):
        self.plugins: Dict[str, BasePlugin] = {}
    
    def register(self, plugin: BasePlugin):
        """注册插件"""
        if plugin.name in self.plugins:
            raise ValueError(f"插件 {plugin.name} 已注册")
        
        self.plugins[plugin.name] = plugin
        plugin.logger.info(f"插件已注册: {plugin.name}")
    
    def unregister(self, plugin_name: str):
        """注销插件"""
        if plugin_name in self.plugins:
            plugin = self.plugins[plugin_name]
            del self.plugins[plugin_name]
            plugin.logger.info(f"插件已注销: {plugin_name}")
    
    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """获取插件"""
        return self.plugins.get(plugin_name)
    
    def list_plugins(self) -> list:
        """列出所有插件"""
        return list(self.plugins.keys())
    
    async def load_all_plugins(self):
        """加载所有插件"""
        for plugin in self.plugins.values():
            try:
                await plugin.on_load()
                plugin.logger.info(f"插件加载完成: {plugin.name}")
            except Exception as e:
                plugin.logger.error(f"插件加载失败 {plugin.name}: {e}", exc_info=True)
    
    async def unload_all_plugins(self):
        """卸载所有插件"""
        for plugin in self.plugins.values():
            try:
                await plugin.on_unload()
                plugin.logger.info(f"插件卸载完成: {plugin.name}")
            except Exception as e:
                plugin.logger.error(f"插件卸载失败 {plugin.name}: {e}", exc_info=True)


# 全局插件注册表
plugin_registry = PluginRegistry()