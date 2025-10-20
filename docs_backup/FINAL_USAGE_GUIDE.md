# 项目最终使用指南

本指南将帮助您正确配置和使用 Telegram 机器人，特别是代理配置部分。

## 项目概述

这是一个功能强大的 Telegram 机器人，专门用于克隆和保存来自公开和私密频道的消息内容。支持流量监控、批量下载、自定义配置等功能。

## 快速开始

### 1. 环境准备

确保您的系统已安装以下依赖：
- Python 3.8+
- pip
- ffmpeg
- git

### 2. 克隆项目

```bash
git clone https://github.com/liwoyuandiane/TG-Content-Bot-Pro.git
cd TG-Content-Bot-Pro
```

### 3. 创建虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或者在 Windows 上: venv\Scripts\activate
```

### 4. 安装依赖

```bash
pip install -r requirements.txt
```

## 配置说明

### 必需配置

在 `.env` 文件中配置以下必需项：

```bash
# Telegram API 凭证（从 my.telegram.org 获取）
API_ID=your_api_id_here
API_HASH=your_api_hash_here

# Bot Token（从 @BotFather 获取）
BOT_TOKEN=your_bot_token_here

# 机器人所有者的 Telegram 用户 ID（从 @userinfobot 获取）
AUTH=your_user_id_here

# MongoDB 连接字符串
MONGO_DB=your_mongodb_connection_string
```

### 代理配置

#### SOCKS5 代理配置

```bash
# SOCKS5 代理配置
TELEGRAM_PROXY_SCHEME=socks5
TELEGRAM_PROXY_HOST=154.201.86.151
TELEGRAM_PROXY_PORT=38512
TELEGRAM_PROXY_USERNAME=Ue9h0D55LS
TELEGRAM_PROXY_PASSWORD=CaqlJmzRWc
```

#### HTTP 代理配置

```bash
# HTTP 代理配置
TELEGRAM_PROXY_SCHEME=http
TELEGRAM_PROXY_HOST=154.201.86.151
TELEGRAM_PROXY_PORT=19496
TELEGRAM_PROXY_USERNAME=wCBcuVZXd6
TELEGRAM_PROXY_PASSWORD=XM1Xdwey02
```

## 启动机器人

### 方法一：使用 start.sh 脚本

```bash
./start.sh
```

### 方法二：直接运行

```bash
python3 -m main
```

### 方法三：使用 Docker

```bash
docker-compose up -d
```

## 测试代理配置

在启动机器人之前，您可以测试代理配置是否正确：

```bash
# 测试 SOCKS5 代理
TELEGRAM_PROXY_SCHEME=socks5 TELEGRAM_PROXY_HOST=154.201.86.151 TELEGRAM_PROXY_PORT=38512 TELEGRAM_PROXY_USERNAME=Ue9h0D55LS TELEGRAM_PROXY_PASSWORD=CaqlJmzRWc python3 test_proxy_complete.py

# 测试 HTTP 代理
TELEGRAM_PROXY_SCHEME=http TELEGRAM_PROXY_HOST=154.201.86.151 TELEGRAM_PROXY_PORT=19496 TELEGRAM_PROXY_USERNAME=wCBcuVZXd6 TELEGRAM_PROXY_PASSWORD=XM1Xdwey02 python3 test_proxy_complete.py
```

## 故障排除

### 1. 代理连接问题

如果遇到代理连接问题，请检查：
- 代理服务器地址和端口是否正确
- 用户名和密码是否正确
- 代理服务器是否正常工作
- 防火墙是否阻止了连接

### 2. Telegram 连接问题

如果机器人无法连接到 Telegram：
- 检查 API 凭证是否正确
- 确认网络连接正常
- 验证代理配置（如果使用代理）

### 3. MongoDB 连接问题

如果无法连接到 MongoDB：
- 检查连接字符串是否正确
- 确认 MongoDB 服务是否正常运行
- 验证网络连接

## 最佳实践

1. **使用虚拟环境**：始终在虚拟环境中运行项目以避免依赖冲突
2. **定期备份**：定期备份 MongoDB 数据和 `.env` 配置文件
3. **安全存储**：确保敏感信息（如 API 凭证、代理密码）的安全存储
4. **监控日志**：定期检查日志文件以发现潜在问题
5. **更新依赖**：定期更新项目依赖以获取最新功能和安全修复

## 支持和文档

- 详细配置说明：[PROXY_CONFIGURATION.md](PROXY_CONFIGURATION.md)
- 使用代理运行机器人：[USAGE_WITH_PROXY.md](USAGE_WITH_PROXY.md)
- 代理故障排除：[SOCKS5_PROXY_SOLUTION.md](SOCKS5_PROXY_SOLUTION.md)