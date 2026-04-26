# TG Content Bot Pro

A stable Telegram bot to save restricted messages from public and private channels.

[Telegram](https://t.me/tgxxtq)

---

## 🔧 Features

- Extract content from public and private channels/groups
- Batch processing (up to 10 files)
- Traffic monitoring and limits
- User authorization management
- Premium user support
- MongoDB database
- Docker support

---

## ⚡ Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/help` | Show help |
| `/plan` | Check account info |
| `/batch` | Batch extract messages |
| `/cancel` | Cancel current task |
| `/authorize` | Add authorized user (admin) |
| `/unauthorize` | Remove authorized user (admin) |
| `/authorized` | List authorized users (admin) |
| `/upgrade` | Upgrade user to premium (admin) |
| `/downgrade` | Downgrade user (admin) |
| `/history` | View forward history (admin) |
| `/clearhistory` | Clear history (admin) |
| `/stats` | View bot statistics (admin) |
| `/traffic` | View traffic stats |
| `/queue` | View queue status (admin) |
| `/sessions` | List all sessions (admin) |
| `/addsession` | Add session (admin) |
| `/delsession` | Delete session (admin) |
| `/mysession` | View my session |

---

## ⚙️ Required Variables

| Variable | Description | Where to Get |
|----------|-------------|--------------|
| `API_ID` | Telegram API ID | [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | Telegram API Hash | [my.telegram.org](https://my.telegram.org) |
| `BOT_TOKEN` | Bot Token | [@BotFather](https://t.me/BotFather) |
| `AUTH` | Owner User ID | [@userinfobot](https://t.me/userinfobot) |
| `MONGO_DB` | MongoDB Connection String | [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) |
| `ENCRYPTION_KEY` | Encryption Key (16-128 chars) | Custom |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SESSION` | Pyrogram session string | - |
| `FORCESUB` | Forced subscription channel | - |
| `LOG_LEVEL` | Log level | INFO |
| `HEALTH_CHECK_PORT` | Health check port | 28089 |
| `FREEMIUM_LIMIT` | Free user batch limit | 0 |
| `PREMIUM_LIMIT` | Premium user batch limit | 10 |

---

## 🚀 Deployment

### Docker (Recommended)

```bash
docker run -d \
  --name tg-bot \
  -e API_ID=your_api_id \
  -e API_HASH=your_api_hash \
  -e BOT_TOKEN=your_bot_token \
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

### VPS / Local

```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot
python3 -m main
```

### Render

1. Fork the repo
2. Create a new Web Service on Render
3. Connect your GitHub repo
4. Set environment variables
5. Deploy

---

## 📖 How to Use

1. Send any message link to the bot
2. Bot will automatically forward to you

Supported link formats:
- Public: `https://t.me/channelname/messageid`
- Private: `https://t.me/c/chatid/messageid`

---

## 🗄️ MongoDB Setup

1. Sign up at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a free cluster
3. Create database user
4. Get connection string:

```
mongodb+srv://<username>:<password>@cluster.mongodb.net/tgbot?retryWrites=true&w=majority
```

---

## 📄 License

MIT License