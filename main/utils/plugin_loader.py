"""插件加载器"""
import sys
import logging
import importlib
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger(__name__)


def load_plugins(plugin_name: str) -> Any:
    """加载插件"""
    try:
        path = Path(f"main/plugins/{plugin_name}.py")
        module_name = f"main.plugins.{plugin_name}"
        
        # 检查模块是否已加载
        if module_name in sys.modules:
            # 重新加载模块
            module = sys.modules[module_name]
            importlib.reload(module)
            logger.debug(f"重新加载插件: {plugin_name}")
        else:
            # 首次加载模块
            spec = importlib.util.spec_from_file_location(module_name, path)
            module = importlib.util.module_from_spec(spec)
            module.logger = logging.getLogger(plugin_name)
            
            spec.loader.exec_module(module)
            sys.modules[module_name] = module
            logger.debug(f"首次加载插件: {plugin_name}")
        
        logger.info(f"成功加载插件: {plugin_name}")
        return module
    except Exception as e:
        logger.error(f"加载插件 {plugin_name} 失败: {e}", exc_info=True)
        raise


def unload_plugins(plugin_name: str) -> bool:
    """卸载插件"""
    try:
        module_name = f"main.plugins.{plugin_name}"
        if module_name in sys.modules:
            del sys.modules[module_name]
            logger.info(f"成功卸载插件: {plugin_name}")
            return True
        else:
            logger.warning(f"插件未加载: {plugin_name}")
            return False
    except Exception as e:
        logger.error(f"卸载插件 {plugin_name} 失败: {e}", exc_info=True)
        return False