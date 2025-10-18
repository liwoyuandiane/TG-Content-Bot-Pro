#!/usr/bin/env python3
"""测试插件加载"""

import sys
import os

# 添加项目路径
project_path = os.path.dirname(os.path.abspath(__file__))
if project_path not in sys.path:
    sys.path.insert(0, project_path)

def test_plugin_loading():
    """测试插件加载"""
    try:
        print("开始测试插件加载...")
        
        # 导入必要的模块
        from main.core.plugin_manager import plugin_manager
        from main.config import settings
        
        print("✅ 成功导入模块")
        
        # 发现插件
        plugins = plugin_manager.discover_plugins()
        print(f"🔍 发现插件: {plugins}")
        
        # 加载所有插件
        results = plugin_manager.load_all_plugins()
        print(f"📊 插件加载结果: {results}")
        
        # 检查特定插件
        if "start" in results:
            print(f"✅ 启动插件加载状态: {'成功' if results['start'] else '失败'}")
        else:
            print("❌ 未找到启动插件")
            
        if "frontend" in results:
            print(f"✅ 前端插件加载状态: {'成功' if results['frontend'] else '失败'}")
        else:
            print("❌ 未找到前端插件")
        
        print("✅ 插件测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 插件测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_plugin_loading()
    sys.exit(0 if success else 1)