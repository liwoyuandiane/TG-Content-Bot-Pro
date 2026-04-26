"""应用主入口"""
import sys
import logging
import asyncio
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# 健康检查处理器
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>TG Content Bot Pro</h1><p>Status: Running</p><p><a href="/health">Health Check</a></p></body></html>')
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        # 静默日志，避免干扰主应用日志
        pass

def start_health_server():
    """启动健康检查HTTP服务器"""
    port = int(os.getenv('HEALTH_CHECK_PORT', '28089'))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logging.info(f"Health check server started on port {port}")
    server.serve_forever()

# 手动加载环境变量
try:
    from decouple import Config, RepositoryEnv
    env_path = os.path.join(os.getcwd(), '.env')
    if os.path.exists(env_path):
        env_config = Config(RepositoryEnv(env_path))
        
        # 加载关键环境变量
        env_vars = [
            'API_ID', 'API_HASH', 'BOT_TOKEN', 'AUTH', 'MONGO_DB',
            'FORCESUB', 'SESSION', 'HEALTH_CHECK_PORT'
        ]
        
        for key in env_vars:
            try:
                value = env_config(key)
                os.environ[key] = str(value)
            except Exception:
                pass  # 变量不存在，跳过
except Exception:
    pass  # decouple库不可用，跳过

# 设置日志
log_level_name = os.getenv('LOG_LEVEL', 'WARNING')
log_level = getattr(logging, log_level_name.upper(), logging.WARNING)
logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=log_level)

from .app import main

def enhanced_main():
    """增强的主函数，启动HTTP健康检查服务器和Telegram机器人"""
    # 在后台启动健康检查服务器
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # 启动原有的Telegram机器人
    main()

if __name__ == "__main__":
    enhanced_main()