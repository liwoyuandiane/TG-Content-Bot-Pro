# AGENTS.md

## Build & Run

```bash
# Docker Run（推荐 - 使用 GitHub Actions 自动构建的镜像）
docker run -d --name tg-content-bot-pro \
  -e API_ID=your_api_id \
  -e API_HASH=your_api_hash \
  -e BOT_TOKEN=your_bot_token \
  -e AUTH=your_user_id \
  -e MONGO_DB=your_mongodb_url \
  -e ENCRYPTION_KEY=your_key \
  -p 28089:28089 \
  ghcr.io/liwoyuandiane/tg-content-bot-pro:latest

# 或使用 .env 文件
docker run -d --name tg-content-bot-pro \
  --env-file .env \
  -p 28089:28089 \
  ghcr.io/liwoyuandiane/tg-content-bot-pro:latest

# Docker Compose（本地构建）
cd /你的运行目录/TG-Content-Bot-Pro
docker-compose up -d --build

# 检查日志
docker logs tg-content-bot-pro --tail 20
```

**镜像地址：** `ghcr.io/liwoyuandiane/tg-content-bot-pro:latest`（GitHub Actions 自动构建）

**重要：** Session 文件持久化到 `./sessions/`，重建容器不会丢失，避免 FLOOD_WAIT。

## 更新日志

### 2026-04-29
- 移除 plugins/ 目录（所有插件），精简代码 88%
- 新增 handlers.py 统一处理所有命令
- 优化 message_service.py 智能获取方案
- 修复 Pyrogram patches 导致的问题，已移除 patches
- 添加 API_ID 变化自动清理 session
- 优化 Docker 配置，持久化 sessions 目录
- 更新 README.md 和 AGENTS.md 文档
- AGENTS.md 不上传到 GitHub（已加入 .gitignore）
- BotClient.session 存储到数据库，无需本地持久化

## Architecture

- **Entry**: `start.sh` → `python3 -m main`
- **Bot client** (`client_manager.bot`): sends messages to users
- **Userbot client** (`client_manager.userbot`): accesses private channels (t.me/c/xxx)
- **Message flow**: `handlers.py` → `message_service.py` → `bot.send_*()`
- **Database**: MongoDB via `database.py`

## Critical: Message Forwarding

**智能获取方案：**
1. 先尝试 `bot.get_messages()` 直接获取（公开频道/群组）
2. 失败则用 `userbot.get_messages()` 获取
3. 用 `bot.send_video()` 等发送给用户

**注意：**
- userbot 获取的 file_id 和 bot 不兼容，可能导致 MEDIA_EMPTY
- 成功时不显示提示，失败时才显示错误

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `FLOOD_WAIT_X` | Bot token rate-limited | Wait X seconds, or switch to backup bot token in `.env` |
| `empty: true` from get_messages | Channel access issue or message deleted | Check if userbot is in channel |
| `MEDIA_EMPTY` | userbot file_id incompatible with bot | 该消息无法转发（受限内容） |
| `Peer id invalid` | Stale peer cache | 忽略，不影响功能 |

## Environment Variables

```
API_ID, API_HASH, BOT_TOKEN, AUTH, MONGO_DB
SESSION (optional — for private channel access)
LOG_LEVEL=DEBUG
```

## Key Files

- `main/services/message_service.py` — core forwarding logic
- `main/handlers.py` — all command handlers
- `main/core/clients.py` — Pyrogram client init
- `main/app.py` — application entry, session cleanup
- `.env` — credentials

## Constraints

- **No download/upload** — use Telegram file_id references only
- **Always send via bot** (`client.send_*`), never via userbot
- Docker image: Alpine-based, ~193MB
- **换机器人时自动清理 session** — API_ID 变化时自动删除旧 session
- **AGENTS.md 不上传到 GitHub** — 已加入 .gitignore