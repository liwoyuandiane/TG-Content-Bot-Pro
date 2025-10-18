"""插件管理器模块"""
import os
import sys
import logging
import importlib
import importlib.util
from typing import Dict, Any, Optional, List
from pathlib import Path

from ..utils.plugin_loader import load_plugins
from ..exceptions.base import BaseBotException

logger = logging.getLogger(__name__)


class PluginError(BaseBotException):
    """插件相关异常"""
    def __init__(self, message: str):
        super().__init__(message, "PLUGIN_ERROR")


class PluginManager:
    """插件管理器"""
    
    def __init__(self, plugins_dir: str = "main/plugins"):
        self.plugins_dir = plugins_dir
        self.plugins: Dict[str, Any] = {}
        self.loaded_plugins: List[str] = []
        
    def discover_plugins(self) -> List[str]:
        """发现所有可用插件"""
        plugins = []
        if os.path.exists(self.plugins_dir):
            for file_path in Path(self.plugins_dir).glob("*.py"):
                if file_path.name != "__init__.py":
                    plugin_name = file_path.stem
                    plugins.append(plugin_name)
        return plugins
    
    def load_plugin(self, plugin_name: str) -> bool:
        """加载单个插件"""
        try:
            if plugin_name in self.loaded_plugins:
                logger.debug(f"插件已加载: {plugin_name}")
                return True
                
            module = load_plugins(plugin_name)
            self.plugins[plugin_name] = module
            self.loaded_plugins.append(plugin_name)
            logger.info(f"成功加载插件: {plugin_name}")
            return True
        except Exception as e:
            logger.error(f"加载插件失败 {plugin_name}: {e}")
            return False
    
    def load_all_plugins(self) -> Dict[str, bool]:
        """加载所有插件"""
        results = {}
        plugin_names = self.discover_plugins()
        
        logger.info(f"发现 {len(plugin_names)} 个插件: {', '.join(plugin_names)}")
        
        for plugin_name in plugin_names:
            results[plugin_name] = self.load_plugin(plugin_name)
        
        return results
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """卸载插件"""
        try:
            if plugin_name in self.plugins:
                # 从已加载列表中移除
                if plugin_name in self.loaded_plugins:
                    self.loaded_plugins.remove(plugin_name)
                
                # 从插件字典中移除
                del self.plugins[plugin_name]
                
                # 从sys.modules中移除（如果存在）
                module_name = f"main.plugins.{plugin_name}"
                if module_name in sys.modules:
                    del sys.modules[module_name]
                
                logger.info(f"成功卸载插件: {plugin_name}")
                return True
            else:
                logger.warning(f"插件未加载: {plugin_name}")
                return False
        except Exception as e:
            logger.error(f"卸载插件失败 {plugin_name}: {e}")
            return False
    
    def reload_plugin(self, plugin_name: str) -> bool:
        """重新加载插件"""
        try:
            # 先卸载插件
            self.unload_plugin(plugin_name)
            
            # 重新加载插件
            return self.load_plugin(plugin_name)
        except Exception as e:
            logger.error(f"重新加载插件失败 {plugin_name}: {e}")
            return False
    
    def get_plugin(self, plugin_name: str) -> Optional[Any]:
        """获取已加载的插件"""
        return self.plugins.get(plugin_name)
    
    def list_loaded_plugins(self) -> List[str]:
        """列出已加载的插件"""
        return self.loaded_plugins.copy()
    
    def is_plugin_loaded(self, plugin_name: str) -> bool:
        """检查插件是否已加载"""
        return plugin_name in self.loaded_plugins


# 全局插件管理器实例
plugin_manager = PluginManager()