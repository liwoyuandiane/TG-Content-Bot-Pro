# AGENTS.md

## Quick Start

```bash
# Development
python3 -m main

# Docker
docker-compose up -d

# Health check
curl http://localhost:28089/health
```

## Required Env Variables

- `API_ID` - Telegram API ID (from my.telegram.org)
- `API_HASH` - Telegram API Hash (32 chars)
- `BOT_TOKEN` - Bot token (from @BotFather)
- `AUTH` - Owner user ID(s), comma-separated
- `MONGO_DB` - MongoDB connection string
- `ENCRYPTION_KEY` - Encryption key (3-128 chars, required)

## Key Commands

- `/start` - Initialize bot
- `/batch` - Batch forward messages (owner only, max 100)
- `/traffic` - View traffic stats
- `/queue` - Queue status (owner)

## Architecture

- **Entry**: `main/app.py` or `python3 -m main`
- **Plugins**: `main/plugins/*.py` - Each file is a command handler
- **Services**: `main/services/*.py` - Business logic
- **Core**: `main/core/` - Clients, DB, plugin manager
- **Config**: `main/config.py` - Uses `python-decouple`

## Single Instance Lock

The app creates `.app.lock` to prevent multiple instances. Delete it if the previous process crashed.

## Plugin System

Plugins in `main/plugins/` are auto-loaded. Each can define handlers for Telegram messages. See `message_handler.py` for the main message processing logic.

## Database

MongoDB is required. Collections: `users`, `message_history`, `batch_tasks`, `settings`. Indexes auto-created on first run.

## Known Quirks

- `FREEMIUM_LIMIT=0` by default (free users cannot batch)
- `PREMIUM_LIMIT=10` default (not 100 as README states - see config.py:94)
- Health server runs on port 28089 (configurable via `HEALTH_CHECK_PORT`)
- App uses both Telethon and Pyrogram clients (`client_manager` in `main/core/clients.py`)