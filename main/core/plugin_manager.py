"""插件管理器模块"""
import os
import sys
import logging
import importlib
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from ..utils.plugin_loader import load_plugins
from ..exceptions.base import BaseBotException

logger = logging.getLogger(__name__)


class PluginError(BaseBotException):
    """插件相关异常"""
    def __init__(self, message: str):
        super().__init__(message, "PLUGIN_ERROR")


class PluginState:
    """插件状态枚举"""
    DISCOVERED = "discovered"
    LOADED = "loaded"
    UNLOADED = "unloaded"
    ERROR = "error"


class PluginInfo:
    """插件信息"""
    def __init__(self, name: str, file_path: Path):
        self.name = name
        self.file_path = file_path
        self.state = PluginState.DISCOVERED
        self.module = None
        self.load_error = None
        self.dependencies: List[str] = []
        self.metadata: Dict[str, Any] = {}


class PluginManager:
    """插件管理器"""
    
    def __init__(self, plugins_dir: str = "main/plugins"):
        self.plugins_dir = plugins_dir
        self.plugin_infos: Dict[str, PluginInfo] = {}
        self.loaded_plugins: List[str] = []
        self._discovered = False
    
    def discover_plugins(self) -> List[str]:
        """发现所有可用插件"""
        if self._discovered:
            return list(self.plugin_infos.keys())
        
        plugins = []
        plugins_dir_path = Path(self.plugins_dir)
        if plugins_dir_path.exists():
            for file_path in plugins_dir_path.glob("*.py"):
                if file_path.name != "__init__.py":
                    plugin_name = file_path.stem
                    plugins.append(plugin_name)
                    self.plugin_infos[plugin_name] = PluginInfo(plugin_name, file_path)
        
        self._discovered = True
        return plugins
    
    def load_plugin(self, plugin_name: str) -> bool:
        """加载单个插件"""
        try:
            if plugin_name in self.loaded_plugins:
                logger.debug(f"插件已加载: {plugin_name}")
                return True
            
            # 检查插件是否存在
            if plugin_name not in self.plugin_infos:
                # 尝试发现插件
                self.discover_plugins()
                if plugin_name not in self.plugin_infos:
                    logger.error(f"插件不存在: {plugin_name}")
                    return False
            
            plugin_info = self.plugin_infos[plugin_name]
            
            # 检查依赖
            if not self._check_dependencies(plugin_name):
                logger.error(f"插件 {plugin_name} 依赖检查失败")
                return False
            
            # 加载插件
            module = load_plugins(plugin_name)
            
            # 解析插件元数据
            self._parse_plugin_metadata(plugin_info, module)
            
            # 更新插件状态
            plugin_info.module = module
            plugin_info.state = PluginState.LOADED
            plugin_info.load_error = None
            
            self.loaded_plugins.append(plugin_name)
            logger.info(f"成功加载插件: {plugin_name}")
            return True
        except Exception as e:
            logger.error(f"加载插件失败 {plugin_name}: {e}")
            if plugin_name in self.plugin_infos:
                self.plugin_infos[plugin_name].state = PluginState.ERROR
                self.plugin_infos[plugin_name].load_error = str(e)
            return False
    
    def _check_dependencies(self, plugin_name: str) -> bool:
        """检查插件依赖"""
        # 简单实现，实际项目中可根据插件元数据检查依赖
        return True
    
    def _parse_plugin_metadata(self, plugin_info: PluginInfo, module: Any) -> None:
        """解析插件元数据"""
        # 检查模块是否有 __plugin_metadata__ 属性
        if hasattr(module, "__plugin_metadata__"):
            plugin_info.metadata = module.__plugin_metadata__
            plugin_info.dependencies = module.__plugin_metadata__.get("dependencies", [])
        
        # 检查模块是否有 __plugin_dependencies__ 属性（旧格式）
        elif hasattr(module, "__plugin_dependencies__"):
            plugin_info.dependencies = module.__plugin_dependencies__
    
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
            if plugin_name in self.loaded_plugins:
                # 从已加载列表中移除
                self.loaded_plugins.remove(plugin_name)
            
            # 更新插件状态
            if plugin_name in self.plugin_infos:
                plugin_info = self.plugin_infos[plugin_name]
                plugin_info.state = PluginState.UNLOADED
                plugin_info.module = None
            
            # 从sys.modules中移除（如果存在）
            module_name = f"main.plugins.{plugin_name}"
            if module_name in sys.modules:
                del sys.modules[module_name]
                # 移除所有相关子模块
                for mod_name in list(sys.modules.keys()):
                    if mod_name.startswith(f"{module_name}."):
                        del sys.modules[mod_name]
            
            logger.info(f"成功卸载插件: {plugin_name}")
            return True
        except Exception as e:
            logger.error(f"卸载插件失败 {plugin_name}: {e}")
            return False
    
    def reload_plugin(self, plugin_name: str) -> bool:
        """重新加载插件"""
        try:
            logger.info(f"开始重新加载插件: {plugin_name}")
            
            # 先卸载插件
            self.unload_plugin(plugin_name)
            
            # 重新加载插件
            success = self.load_plugin(plugin_name)
            
            if success:
                logger.info(f"成功重新加载插件: {plugin_name}")
            else:
                logger.error(f"重新加载插件失败: {plugin_name}")
            
            return success
        except Exception as e:
            logger.error(f"重新加载插件失败 {plugin_name}: {e}")
            return False
    
    def reload_all_plugins(self) -> Dict[str, bool]:
        """重新加载所有插件"""
        results = {}
        loaded_plugins = self.loaded_plugins.copy()
        
        logger.info(f"开始重新加载 {len(loaded_plugins)} 个插件")
        
        # 先卸载所有插件
        for plugin_name in loaded_plugins:
            self.unload_plugin(plugin_name)
        
        # 重新加载所有插件
        for plugin_name in loaded_plugins:
            results[plugin_name] = self.load_plugin(plugin_name)
        
        logger.info(f"重新加载完成，成功: {sum(results.values())}, 失败: {len(results) - sum(results.values())}")
        return results
    
    def get_plugin(self, plugin_name: str) -> Optional[Any]:
        """获取已加载的插件"""
        if plugin_name in self.plugin_infos:
            return self.plugin_infos[plugin_name].module
        return None
    
    def list_loaded_plugins(self) -> List[str]:
        """列出已加载的插件"""
        return self.loaded_plugins.copy()
    
    def is_plugin_loaded(self, plugin_name: str) -> bool:
        """检查插件是否已加载"""
        return plugin_name in self.loaded_plugins
    
    def get_plugin_status(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """获取插件状态"""
        if plugin_name not in self.plugin_infos:
            return None
        
        plugin_info = self.plugin_infos[plugin_name]
        return {
            "name": plugin_name,
            "state": plugin_info.state,
            "file_path": str(plugin_info.file_path),
            "dependencies": plugin_info.dependencies,
            "metadata": plugin_info.metadata,
            "load_error": plugin_info.load_error
        }
    
    def get_all_plugin_statuses(self) -> Dict[str, Dict[str, Any]]:
        """获取所有插件状态"""
        # 确保插件已发现
        self.discover_plugins()
        
        statuses = {}
        for plugin_name, plugin_info in self.plugin_infos.items():
            statuses[plugin_name] = self.get_plugin_status(plugin_name)
        return statuses


# 全局插件管理器实例
plugin_manager = PluginManager()