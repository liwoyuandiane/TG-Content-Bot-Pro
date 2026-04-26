# AGENTS.md

## Entry

```bash
python3 -m main        # or: python3 main/app.py
./start.sh             # validates all required env vars first
docker-compose up -d
curl http://localhost:28089/health
```

## Required Env Variables

- `API_ID` - Telegram API ID (from my.telegram.org)
- `API_HASH` - Telegram API Hash (32 chars)
- `BOT_TOKEN` - Bot token (from @BotFather)
- `AUTH` - Owner user ID(s), comma-separated
- `MONGO_DB` - MongoDB connection string
- `ENCRYPTION_KEY` - Encryption key (3-128 chars, checked by `start.sh`)

## Optional Env Variables

- `DB_RESET=true` - Reset DB on startup (clears collections, recreates indexes, re-adds auth users)
- `SESSION` - User session string (for accessing private channels via userbot)
- `FORCESUB` - Required subscribe channel username (without @)
- `HEALTH_CHECK_PORT` - Defaults to 28089
- `LOG_LEVEL` - Defaults to INFO

## Architecture

- **Entry**: `main/app.py` (async main loop, plugin loading, startup/shutdown lifecycle)
- **Health server**: spawned as a daemon thread in `main/app.py`, port 28089
- **Dual clients**: Telethon (`bot`) for event handlers; Pyrogram (`pyrogram_bot`) for bot commands. Both run simultaneously.
- **Plugins**: auto-discover and load from `main/plugins/*.py`. Each can define message handlers.
- **Config**: `main/config.py` - validates all settings at import time (raises `ConfigError` if invalid)
- **Core**: `main/core/` - clients, DB, plugin manager, task queue
- **Services**: `main/services/*.py` - session, permission, user, traffic services
- **Utils**: `main/utils/` - plugin_loader, security, session_utils, logging_config

## Database

MongoDB required. Collections: `users`, `message_history`, `batch_tasks`, `settings`. Indexes auto-created on startup.

## Single Instance Lock

`.app.lock` file prevents multiple instances. Delete it if the previous process crashed (no zombie pid check).

## Batch Limits (Non-obvious)

- `FREEMIUM_LIMIT=0` - free users **cannot** batch
- `PREMIUM_LIMIT=10` (not 100 as README claims)

## Bot Commands (as registered in code)

User: `/start`, `/help`, `/plan`, `/batch`, `/cancel`

Admin: `/authorize`, `/unauthorize`, `/authorized`, `/upgrade`, `/downgrade`, `/history`, `/clearhistory`, `/sessions`, `/addsession`, `/generatesession`, `/delsession`, `/mysession`, `/queue`

## Note

App starts in **degraded mode** (health check only) if Telegram API credentials are invalid. The bot won't function but won't crash either.