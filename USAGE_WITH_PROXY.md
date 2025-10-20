# 使用代理运行机器人

本指南将帮助您配置和使用代理来运行 Telegram 机器人。

## 配置 SOCKS5 代理

### 1. 修改 .env 文件

在项目根目录的 `.env` 文件中添加以下配置：

```bash
# SOCKS5 代理配置
TELEGRAM_PROXY_SCHEME=socks5
TELEGRAM_PROXY_HOST=154.201.86.151
TELEGRAM_PROXY_PORT=38512
TELEGRAM_PROXY_USERNAME=Ue9h0D55LS
TELEGRAM_PROXY_PASSWORD=CaqlJmzRWc
```

### 2. 启动机器人

```bash
# 使用 start.sh 脚本启动
./start.sh

# 或者直接运行
python3 -m main
```

## 配置 HTTP 代理

### 1. 修改 .env 文件

在项目根目录的 `.env` 文件中添加以下配置：

```bash
# HTTP 代理配置
TELEGRAM_PROXY_SCHEME=http
TELEGRAM_PROXY_HOST=154.201.86.151
TELEGRAM_PROXY_PORT=19496
TELEGRAM_PROXY_USERNAME=wCBcuVZXd6
TELEGRAM_PROXY_PASSWORD=XM1Xdwey02
```

### 2. 启动机器人

```bash
# 使用 start.sh 脚本启动
./start.sh

# 或者直接运行
python3 -m main
```

## 测试代理配置

### 使用测试脚本

项目包含一个代理测试脚本，可以帮助您验证代理配置是否正确：

```bash
# 运行代理测试
python3 test_proxy.py
```

### 使用启动脚本测试代理

您也可以在启动机器人之前测试代理配置：

```bash
# 设置环境变量并启动
TEST_PROXY=1 ./start.sh
```

## Docker 中使用代理

如果您使用 Docker 部署，需要在 `docker-compose.yml` 中添加环境变量：

```yaml
version: "3.8"

services:
  tg-bot:
    build: .
    container_name: tg-content-bot
    restart: unless-stopped
    environment:
      # 必需配置
      API_ID: ${API_ID}
      API_HASH: ${API_HASH}
      BOT_TOKEN: ${BOT_TOKEN}
      AUTH: ${AUTH}
      MONGO_DB: ${MONGO_DB}
      
      # 代理配置
      TELEGRAM_PROXY_SCHEME: socks5
      TELEGRAM_PROXY_HOST: 154.201.86.151
      TELEGRAM_PROXY_PORT: 38512
      TELEGRAM_PROXY_USERNAME: Ue9h0D55LS
      TELEGRAM_PROXY_PASSWORD: CaqlJmzRWc
      
      # 可选配置
      SESSION: ${SESSION:-}
      FORCESUB: ${FORCESUB:-}
```

## 故障排除

### 1. 连接问题

如果遇到连接问题，请检查：

- 代理服务器地址和端口是否正确
- 用户名和密码是否正确
- 代理服务器是否正常工作
- 防火墙是否阻止了连接

### 2. 认证失败

如果代理认证失败：

- 确保用户名和密码正确无误
- 检查密码中是否包含特殊字符，可能需要转义
- 尝试使用无认证的代理进行测试

### 3. 日志信息

查看日志文件获取更多错误信息：

```bash
# 查看日志
tail -f logs/bot.log

# 或者使用 Docker 查看日志
docker-compose logs -f
```

## 最佳实践

1. **优先使用 SOCKS5 代理**：SOCKS5 代理在 Telegram 客户端中有更好的支持
2. **定期测试代理**：定期测试代理连接以确保其正常工作
3. **备份配置**：备份您的 `.env` 文件以防止配置丢失
4. **安全存储**：确保代理认证信息的安全存储，不要将其提交到版本控制系统中