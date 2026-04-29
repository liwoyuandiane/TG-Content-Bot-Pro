# AGENTS.md

## Build & Run

```bash
# Docker Compose (推荐 - 自动持久化到当前目录)
cd /你的运行目录/TG-Content-Bot-Pro
docker-compose up -d --build

# Docker Run (手动指定持久化目录)
docker run -d --name tg-content-bot-pro \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/sessions:/app/sessions \
  -p 28089:28089 \
  tg-content-bot-pro-tg-content-bot-pro

# 检查日志
docker logs tg-content-bot-pro --tail 20
```

**重要：** Session 文件持久化到 `./sessions/`，重建容器不会丢失，避免 FLOOD_WAIT。

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

## Pyrogram Patches (clients.py)

已移除 Pyrogram patches，因为会干扰 bot 的正常工作。如果遇到 peer 相关错误，需要在应用层处理。

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
