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

## ⚙️ 环境变量

### 必需

| 变量 | 说明 | 获取 |
|------|------|------|
| `API_ID` | Telegram API ID | [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | Telegram API Hash | [my.telegram.org](https://my.telegram.org) |
| `BOT_TOKEN` | Bot Token | [@BotFather](https://t.me/BotFather) |
| `AUTH` | 管理员 ID | [@userinfobot](https://t.me/userinfobot) |
| `MONGO_DB` | MongoDB 连接串 | [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) |
| `ENCRYPTION_KEY` | 加密密钥 (4-64位) | 自定义 |

### 可选

| 变量 | 说明 | 默认 |
|------|------|------|
| `SESSION` | Pyrogram 会话串 | - |
| `FORCESUB` | 强制订阅频道 | tgxxtq |
| `LOG_LEVEL` | 日志级别 | INFO |
| `HEALTH_CHECK_PORT` | 健康检查端口 | 28089 |
| `FREEMIUM_LIMIT` | 免费用户限制 | 0 |
| `PREMIUM_LIMIT` | Premium 限制 | 10 |

---

## 🚀 部署方式

### Docker 运行容器（推荐）

```bash
docker run -d \
  --name tg-bot \
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

## ⚡ 命令列表

| 命令 | 说明 | 权限 |
|------|------|------|
| `/start` | 启动机器人 | 所有人 |
| `/help` | 显示帮助 | 所有人 |
| `/plan` | 账户信息 | 所有人 |
| `/batch` | 批量获取 | 授权用户 |
| `/cancel` | 取消任务 | 授权用户 |
| `/authorize` | 添加授权 | 管理员 |
| `/unauthorize` | 移除授权 | 管理员 |
| `/authorized` | 授权列表 | 管理员 |
| `/upgrade` | 升级 Premium | 管理员 |
| `/downgrade` | 降级用户 | 管理员 |
| `/history` | 转发历史 | 管理员 |
| `/clearhistory` | 清除历史 | 管理员 |
| `/stats` | 机器人统计 | 管理员 |
| `/traffic` | 流量统计 | 所有人 |
| `/queue` | 队列状态 | 管理员 |
| `/sessions` | SESSION 列表 | 管理员 |
| `/addsession` | 添加 SESSION | 管理员 |
| `/delsession` | 删除 SESSION | 管理员 |
| `/mysession` | 我的 SESSION | 管理员 |

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

## 📄 许可证

MIT License