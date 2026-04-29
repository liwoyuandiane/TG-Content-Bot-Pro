# TG Content Bot Pro

Telegram 受限内容保存机器人，支持从公开和私密频道获取消息。

[Telegram](https://t.me/tgxxtq)

---

## 🔧 功能特性

- 支持公开和私密频道消息获取
- 智能获取：先尝试 bot 直接获取，失败再用 userbot
- 批量处理（最多10条）
- 流量监控和限制
- 用户授权管理
- Premium 用户支持
- Docker 支持，Session 持久化到数据库

---

## 🚀 部署方式

### Docker Run（推荐 - 使用 GitHub Actions 自动构建的镜像）

```bash
docker run -d --name tg-content-bot-pro \
  -e API_ID=your_api_id \
  -e API_HASH=your_api_hash \
  -e BOT_TOKEN=your_bot_token \
  -e AUTH=your_user_id \
  -e MONGO_DB=your_mongodb_url \
  -e ENCRYPTION_KEY=your_key \
  -v $(pwd)/logs:/app/logs \
  -p 28089:28089 \
  ghcr.io/liwoyuandiane/tg-content-bot-pro:latest
```

或使用 `.env` 文件：

```bash
docker run -d --name tg-content-bot-pro \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  -p 28089:28089 \
  ghcr.io/liwoyuandiane/tg-content-bot-pro:latest
```

**镜像地址：** `ghcr.io/liwoyuandiane/tg-content-bot-pro:latest`（GitHub Actions 自动构建）

### Docker Compose（本地构建）

```bash
git clone https://github.com/liwoyuandiane/TG-Content-Bot-Pro.git
cd TG-Content-Bot-Pro
cp .env.example .env
nano .env  # 编辑配置
docker-compose up -d --build
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

## ❓ 常见问题

### 1. 链接解析失败 / 消息无法获取
**问题**：`链接解析失败，请检查链接格式`

**原因**：
- 发送的链接格式不正确
- Bot 无法访问该群组/频道

**解决方案**：
- 确保链接格式正确：`https://t.me/username/message_id` 或 `https://t.me/c/chatid/message_id`
- 如果是群组消息，需要添加 Bot 到群组，或配置 SESSION

### 2. 公开群组消息无法转发
**问题**：转发公开群组（如 @starlink_2077）消息失败

**原因**：
- Telegram 限制：Bot 无法直接访问公开群组的消息
- 用户账号可以访问，但获取的 file_id 不能给机器人用

**解决方案**：
- 将机器人添加到该群组中，成为成员后再试转发

### 3. 未配置 SESSION
**问题**：`未配置 SESSION，无法访问受限内容`

**原因**：访问私有频道/群组需要用户账号权限，Bot 无法直接访问

**解决方案**：
- 使用 `/generatesession` 命令生成 SESSION
- 或在 `.env` 中配置 `SESSION` 环境变量

### 4. FloodWaitError（限流）
**问题**：`A wait of X seconds is required`

**原因**：Telegram API 限流，通常由频繁重启或多次连接失败引起

**解决方案**：
- 等待指定时间（通常 30 分钟到 24 小时）
- 等待期间**不要重启容器**，否则会延长等待时间
- 等待结束后自动恢复

### 5. MongoDB 连接失败
**问题**：`数据库连接失败` 或 `保存失败`

**原因**：
- MongoDB 连接串配置错误
- MongoDB Atlas IP 白名单未添加服务器 IP
- 网络连接问题

**解决方案**：
- 检查 `MONGO_DB` 环境变量是否正确
- 在 MongoDB Atlas 中添加服务器 IP 到白名单（IP Access List）
- 确保 MongoDB Atlas 集群状态正常

### 6. SESSION 保存失败
**问题**：`SESSION 保存失败，请稍后重试`

**原因**：
- MongoDB 数据库连接问题
- 用户数据写入权限问题

**解决方案**：
- 检查 MongoDB 连接是否正常
- 检查 Atlas 白名单设置
- 等待一段时间后重试

### 7. Bot 无法访问群组消息
**问题**：公开群组消息转发失败

**原因**：
- Telegram Bot API 限制：Bot 无法主动获取群组消息
- Bot 不是群组成员

**解决方案**：
- 将 Bot 添加为群组管理员或成员
- 或配置 SESSION（用户账号）来访问群组

### 8. 单实例运行错误
**问题**：`检测到另一个实例正在运行`

**原因**：已有 Bot 实例在运行

**解决方案**：
```bash
# 停止所有相关容器
docker stop tg-content-bot-pro
docker rm tg-content-bot-pro
# 重新启动
docker run -d --name tg-content-bot-pro \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/sessions:/app/sessions \
  -p 28089:28089 \
  ghcr.io/liwoyuandiane/tg-content-bot-pro:latest
```

### 9. MEDIA_EMPTY 错误
**问题**：`The media you tried to send is invalid`

**原因**：
- userbot 获取的 file_id 和 bot 不兼容
- 消息内容可能已被删除或受限

**解决方案**：
- 该消息无法转发，属于 Telegram 限制
- 尝试其他消息链接

---

## 📄 许可证

MIT License