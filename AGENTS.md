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
- `ENCRYPTION_KEY` - Encryption key (3-128 chars)

## Env Variables (Optional)

- `DB_RESET=true` - Reset database on startup (clears all collections, recreates indexes, adds auth users)
- `SESSION` - User session string for accessing private channels
- `FORCESUB` - Required channel username (without @)

## Commands

- `/start` - Initialize bot, show stats
- `/batch` - Batch forward (owner only, max 100)
- `/cancel` - Cancel batch operation (owner)
- `/traffic` - View traffic stats
- `/queue` - Queue status (owner)
- `/history` - Forward history (owner)
- `/plan` - User tier/plan info

## Architecture

- **Entry**: `main/app.py` or `python3 -m main`
- **Plugins**: `main/plugins/*.py` - Auto-loaded command handlers
- **Services**: `main/services/*.py` - Business logic
- **Core**: `main/core/` - Clients, DB, plugin manager
- **Config**: `main/config.py` - Uses `python-decouple`

## Single Instance Lock

Creates `.app.lock` to prevent multiple instances. Delete it if previous process crashed.

## Plugin System

Plugins auto-load from `main/plugins/`. Each can define handlers for Telegram messages. Main processing in `message_handler.py`.

## Database

MongoDB required. Collections: `users`, `message_history`, `batch_tasks`, `settings`. Indexes auto-created on startup.

## Known Quirks

- `FREEMIUM_LIMIT=0` (free users cannot batch)
- `PREMIUM_LIMIT=10` default (not 100 as README claims)
- Health server port: 28089 (configurable via `HEALTH_CHECK_PORT`)
- App uses both Telethon and Pyrogram clients (`main/core/clients.py`)
- ENCRYPTION_KEY is required (checked in start.sh) - needed to encrypt SESSION storage