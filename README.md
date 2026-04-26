# TG消息提取器 (SaveRestrictedContentBot)

> Telegram 受限内容保存机器人 - 支持公开和私密频道消息克隆

一个功能强大的Telegram机器人，专门用于克隆和保存来自公开和私密频道的消息内容。支持流量监控、批量转发、自定义配置等功能。

## ✨ 核心特性

- ✅ 支持公开频道消息克隆
- ✅ 支持私密频道消息保存
- ✅ 流量监控和限制（每日/每月/累计统计）
- ✅ 批量转发（最多10条）
- ✅ 支持多种媒体类型转发
- ✅ 自适应速率限制
- ✅ 授权访问控制
- ✅ 全中文界面

## 🚀 快速开始

### Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/liwoyuandiane/TG-Content-Bot-Pro.git
cd TG-Content-Bot-Pro

# 2. 配置环境变量
cp .env.example .env
nano .env

# 3. 启动服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f
```

### 使用预构建镜像

```bash
# 拉取镜像
docker pull ghcr.io/liwoyuandiane/tg-content-bot-pro:latest

# 运行容器
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

---

## 📋 环境变量配置

### 必需变量

| 变量名 | 说明 | 获取方式 |
|--------|------|----------|
| `API_ID` | Telegram API ID | [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | Telegram API Hash (32位) | [my.telegram.org](https://my.telegram.org) |
| `BOT_TOKEN` | Bot Token | [@BotFather](https://t.me/BotFather) |
| `AUTH` | 管理员用户ID | [@userinfobot](https://t.me/userinfobot) |
| `MONGO_DB` | MongoDB 连接字符串 | [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) |
| `ENCRYPTION_KEY` | 加密密钥 (16-128位) | 自定义 |

### 可选变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `SESSION` | Pyrogram 会话字符串 | - |
| `FORCESUB` | 强制订阅频道用户名 | - |
| `LOG_LEVEL` | 日志级别 | INFO |
| `HEALTH_CHECK_PORT` | 健康检查端口 | 28089 |
| `FREEMIUM_LIMIT` | 免费用户批量限制 | 0 |
| `PREMIUM_LIMIT` | 付费用户批量限制 | 10 |

---

## 🐳 Docker 部署

### 1. 配置环境变量

```bash
cp .env.example .env
nano .env
```

`.env` 文件内容示例：

```bash
# 必需配置
API_ID=12345678
API_HASH=abcdef1234567890abcdef1234567890
BOT_TOKEN=1234567890:ABCdefGhIJKLMNOPqrstUVwXYz123456
AUTH=123456789
MONGO_DB=mongodb+srv://username:password@cluster.mongodb.net/tgbot?retryWrites=true&w=majority
ENCRYPTION_KEY=your_secure_key_here_at_least_16_chars

# 可选配置
LOG_LEVEL=INFO
```

### 2. 启动服务

```bash
docker-compose up -d
```

### 3. 检查状态

```bash
# 查看日志
docker-compose logs -f

# 健康检查
curl http://localhost:28089/health
```

---

## 📖 使用说明

### 基本命令

| 命令 | 说明 | 权限 |
|------|------|------|
| `/start` | 初始化机器人 | 所有用户 |
| `/help` | 显示帮助 | 所有用户 |
| `/plan` | 查看账户信息 | 所有用户 |
| `/batch` | 批量转发消息 | 授权用户 |
| `/cancel` | 取消当前任务 | 授权用户 |
| `/authorize` | 添加授权用户 | 管理员 |
| `/unauthorize` | 移除授权用户 | 管理员 |
| `/authorized` | 查看授权列表 | 管理员 |
| `/upgrade` | 升级为Premium | 管理员 |
| `/downgrade` | 降级为普通用户 | 管理员 |
| `/history` | 查看转发历史 | 管理员 |
| `/clearhistory` | 清除转发历史 | 管理员 |
| `/traffic` | 查看个人流量 | 所有用户 |
| `/stats` | 查看机器人统计 | 管理员 |
| `/queue` | 查看队列状态 | 管理员 |
| `/sessions` | 查看所有SESSION | 管理员 |
| `/addsession` | 添加SESSION | 管理员 |
| `/delsession` | 删除SESSION | 管理员 |
| `/mysession` | 查看我的SESSION | 管理员 |

### 消息转发

1. 发送任意消息链接到机器人
2. 机器人会自动转发给您

支持的消息链接格式：
- 公开频道：`https://t.me/channelname/messageid`
- 私密频道：`https://t.me/c/chatid/messageid`

---

## 🔧 手动部署

```bash
# 克隆项目
git clone https://github.com/liwoyuandiane/TG-Content-Bot-Pro.git
cd TG-Content-Bot-Pro

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
nano .env

# 启动机器人
python3 -m main
```

---

## 🗄️ MongoDB 注册获取

1. 访问 [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. 注册账号（免费版足够）
3. 创建免费集群（Free Tier）
4. 创建数据库用户
5. 获取连接字符串，格式如下：

```
mongodb+srv://<username>:<password>@<cluster-url>/<database>?retryWrites=true&w=majority
```

**注意**：将 `<password>` 中的特殊字符进行 URL 编码。

---

## 📄 许可证

MIT License