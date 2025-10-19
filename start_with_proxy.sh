#!/bin/bash

# 带代理的启动脚本模板
# 使用方法: 
# 1. 复制此文件为 start_with_proxy_custom.sh
# 2. 在复制的文件中填写您的代理信息
# 3. 运行 ./start_with_proxy_custom.sh

# 设置代理环境变量 (请在自定义副本中填写您的代理信息)
# export HTTP_PROXY=http://username:password@proxy_host:proxy_port
# export HTTPS_PROXY=http://username:password@proxy_host:proxy_port

# 设置Python路径
export PYTHONPATH=.

# 启动程序
echo "启动 TG-Content-Bot-Pro..."
if [[ -n "" ]]; then
    echo "使用代理: "
else
    echo "未设置代理"
fi
echo ""

python3 -m main
