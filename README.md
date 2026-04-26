# TG Content Bot Pro

Telegram 受限内容保存机器人，支持从公开和私密频道获取消息。

[Telegram](https://t.me/tgxxtq)

---

## 🔧 功能特性

- 支持公开和私密频道消息获取
- 批量处理（最多10条）
- 流量监控和限制
- 用户授权管理
- Premium 用户支持
- Docker 支持

---

## 🚀 部署方式

### Docker 运行容器（推荐）

```bash
docker run -d \
  --name tg-content-bot-pro \
  -e API_ID=your_api_id \
  -e API_HASH=your_api_hash \
  -e BOT_TOKEN=your_token \
  -e AUTH=your_user_id \
  -e MONGO_DB=your_mongo_url \
  -e ENCRYPTION_KEY=your_key \
  -p 28089:28089 \
  ghcr.io/liwoyuandiane/tg-content-bot-pro:latest
```

### Docker Compose

```bash
git clone https://github.com/liwoyuandiane/TG-Content-Bot-Pro.git
cd TG-Content-Bot-Pro
cp .env.example .env
nano .env
docker-compose up -d
```

### VPS / 本地

```bash
git clone https://github.com/liwoyuandiane/TG-Content-Bot-Pro.git
cd TG-Content-Bot-Pro
cp .env.example .env
nano .env
pip install -r requirements.txt
python3 -m main
```

---

## 📖 使用方法

1. 发送消息链接给机器人
2. 机器人自动转发给你

支持的链接格式：
- 公开频道：`https://t.me/channelname/messageid`
- 私密频道：`https://t.me/c/chatid/messageid`

---

## ⚙️ 环境变量说明

| 变量名 | 必填 | 示例 | 详细备注 |
|--------|:----:|------|----------|
| `API_ID` | ✅ | `your_api_id` | Telegram API ID，从 [my.telegram.org](https://my.telegram.org) 获取 |
| `API_HASH` | ✅ | `your_api_hash` | Telegram API Hash，32位字符，从 [my.telegram.org](https://my.telegram.org) 获取 |
| `BOT_TOKEN` | ✅ | `your_bot_token` | Bot Token，从 [@BotFather](https://t.me/BotFather) 获取 |
| `AUTH` | ✅ | `your_user_id` | 管理员用户 ID，支持多个用逗号分隔，从 [@userinfobot](https://t.me/userinfobot) 获取 |
| `MONGO_DB` | ✅ | `mongodb+srv://...` | MongoDB 连接串，从 [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) 获取 |
| `ENCRYPTION_KEY` | ❌ | `your_key_here` | 加密密钥，4-64位字符，用于加密 SESSION |
| `SESSION` | ❌ | `Pyrogram session string` | Pyrogram 会话串，用于访问私有频道 |
| `FORCESUB` | ❌ | `tgxxtq` | 强制订阅频道用户名，不带 @ 符号 |
| `LOG_LEVEL` | ❌ | `INFO` | 日志级别，默认 INFO |
| `HEALTH_CHECK_PORT` | ❌ | `28089` | 健康检查端口，默认 28089 |
| `FREEMIUM_LIMIT` | ❌ | `0` | 免费用户批量限制，默认 0 |
| `PREMIUM_LIMIT` | ❌ | `10` | Premium 用户批量限制，默认 10 |

---

## 🗄️ MongoDB 注册

1. 访问 [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. 注册账号，创建免费集群
3. 创建数据库用户
4. 获取连接串：

```
mongodb+srv://<username>:<password>@cluster.mongodb.net/tgbot?retryWrites=true&w=majority
```

---

## ⚡ 常用命令

| 命令 | 说明 |
|------|------|
| `/start` | 启动机器人 |
| `/help` | 显示帮助 |
| `/batch` | 批量获取消息 |
| `/cancel` | 取消任务 |

---

## 📄 许可证

MIT License