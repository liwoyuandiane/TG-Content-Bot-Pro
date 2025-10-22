# TG消息提取器 (SaveRestrictedContentBot)

> Telegram 受限内容保存机器人 - 支持公开和私密频道消息克隆

一个功能强大的Telegram机器人，专门用于克隆和保存来自公开和私密频道的消息内容。支持流量监控、批量下载、自定义配置等功能，具备完善的错误处理和自适应速率限制机制。

[![GitHub stars](https://img.shields.io/github/stars/liwoyuandiane/TG-Content-Bot-Pro?style=social)](https://github.com/liwoyuandiane/TG-Content-Bot-Pro)
[![License](https://img.shields.io/github/license/liwoyuandiane/TG-Content-Bot-Pro)](LICENSE)

## ✨ 特性

- ✅ 支持公开频道消息克隆
- ✅ 支持私密频道消息保存
- ✅ 流量监控和限制（每日/每月/累计统计）
- ✅ 自定义缩略图
- ✅ 批量下载（最多100条）
- ✅ 支持文本、图片、视频、文件
- ✅ 自适应速率限制
- ✅ 强制订阅功能
- ✅ 全中文界面
- ✅ 在线生成 SESSION
- ✅ 授权访问控制

## 🚀 快速开始

### 一键安装（推荐）

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/liwoyuandiane/TG-Content-Bot-Pro/main/install.sh)
```

**安装过程**：
1. 自动检测系统环境
2. 自动安装缺少的依赖（python3, pip, ffmpeg, git 等）
3. 克隆项目代码
4. 创建虚拟环境并安装依赖
5. 提示用户配置环境变量
6. 测试 MongoDB 连接
7. 创建启动脚本

### 一键卸载

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/liwoyuandiane/TG-Content-Bot-Pro/main/install.sh) uninstall
```

**卸载过程**：
1. 停止运行中的机器人进程
2. 删除项目目录及所有相关文件
3. 清理系统服务和 cron 任务
4. 保留 MongoDB 数据库（需手动清理）

**安装完成后**：
```bash
cd ~/TG-Content-Bot-Pro
./start.sh
```

---

## 📋 环境变量

| 变量名 | 说明 | 获取方式 | 必需 |
|--------|------|---------|------|
| API_ID | Telegram API ID | [my.telegram.org](https://my.telegram.org) | ✅ |
| API_HASH | Telegram API Hash | [my.telegram.org](https://my.telegram.org) | ✅ |
| BOT_TOKEN | 机器人Token | [@BotFather](https://t.me/BotFather) | ✅ |
| AUTH | 授权用户ID | [@userinfobot](https://t.me/userinfobot) | ✅ |
| MONGO_DB | MongoDB连接字符串 | [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) | ✅ |
| SESSION | Pyrogram会话字符串 | 运行`python3 get_session.py`生成 | ❌ |
| FORCESUB | 强制订阅频道 | 频道用户名（不带@） | ❌ |
| TELEGRAM_PROXY_SCHEME | Telegram代理协议 | [SOCKS5_PROXY_SOLUTION.md](SOCKS5_PROXY_SOLUTION.md) | ❌ |
| TELEGRAM_PROXY_HOST | Telegram代理主机 | [SOCKS5_PROXY_SOLUTION.md](SOCKS5_PROXY_SOLUTION.md) | ❌ |
| TELEGRAM_PROXY_PORT | Telegram代理端口 | [SOCKS5_PROXY_SOLUTION.md](SOCKS5_PROXY_SOLUTION.md) | ❌ |
| TELEGRAM_PROXY_USERNAME | Telegram代理用户名 | 代理认证用户名 | ❌ |
| TELEGRAM_PROXY_PASSWORD | Telegram代理密码 | 代理认证密码 | ❌ |

---

## 🛠️ 部署方式

### Docker部署（推荐）

```bash
# 克隆项目
git clone https://github.com/liwoyuandiane/TG-Content-Bot-Pro.git
cd TG-Content-Bot-Pro

# 配置环境变量
cp .env.example .env
nano .env  # 编辑配置

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 测试代理配置

项目包含一个代理测试脚本，可以帮助您验证代理配置是否正确：

```bash
# 运行代理测试
python3 test_proxy.py

# 或者使用启动脚本测试代理
TEST_PROXY=1 ./start.sh
```

### 手动部署

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
nano .env  # 编辑配置

# 启动机器人
python3 -m main
```

### 代理配置

机器人支持 SOCKS5 和 HTTP 代理，以解决网络连接问题：

1. **SOCKS5 代理配置**：
   ```bash
   TELEGRAM_PROXY_SCHEME=socks5
   TELEGRAM_PROXY_HOST=154.201.86.151
   TELEGRAM_PROXY_PORT=38512
   TELEGRAM_PROXY_USERNAME=Ue9h0D55LS
   TELEGRAM_PROXY_PASSWORD=CaqlJmzRWc
   ```

2. **HTTP 代理配置**：
   ```bash
   TELEGRAM_PROXY_SCHEME=http
   TELEGRAM_PROXY_HOST=154.201.86.151
   TELEGRAM_PROXY_PORT=19496
   TELEGRAM_PROXY_USERNAME=wCBcuVZXd6
   TELEGRAM_PROXY_PASSWORD=XM1Xdwey02
   ```

3. **Cloudflare Workers Telegram API 代理**：
   如果您的服务器无法直接连接到 Telegram API，可以部署 Cloudflare Workers 作为代理：
   
   - 部署 `cloudflare-worker.js` 到 Cloudflare Workers
   - 在 `.env` 文件中配置：
   ```bash
   TELEGRAM_API_PROXY_URL=https://your-worker.your-account.workers.dev
   ```
   
   详细配置说明请参考 [CLOUDFLARE-WORKER-DEPLOY.md](CLOUDFLARE-WORKER-DEPLOY.md)。

详细配置说明请参考 [PROXY_CONFIGURATION.md](PROXY_CONFIGURATION.md)。

---

## 📖 使用说明

### 基本命令

- `/start` - 初始化机器人，显示个人统计
- `/batch` - 批量下载消息（仅所有者，最多100条）
- `/cancel` - 取消正在进行的批量操作（仅所有者）
- `/traffic` - 查看个人流量统计（每日/每月/累计）
- `/stats` - 查看机器人统计（仅所有者）
- `/history` - 查看最近20次下载记录（仅所有者）
- `/queue` - 查看队列和速率限制状态（仅所有者）
- `/totaltraffic` - 查看总流量统计（仅所有者）
- `/setlimit` - 配置流量限制（仅所有者）
- `/resettraffic` - 重置流量统计（仅所有者）
- `/addsession` - 添加用户SESSION（仅所有者）
- `/delsession` - 删除用户SESSION（仅所有者）
- `/sessions` - 列出所有存储的SESSION（仅所有者）
- `/mysession` - 查看自己的SESSION字符串

### 消息克隆

1. 发送任意消息链接到机器人
2. 机器人会自动下载并发送给您

支持的消息链接格式：
- 公开频道：`https://t.me/channelname/messageid`
- 私密频道：`https://t.me/c/chatid/messageid`
- 机器人频道：`https://t.me/b/chatid/messageid`

### 批量下载

1. 发送`/batch`命令
2. 按提示发送起始消息链接
3. 按提示发送要下载的消息数量（最多100条）

---

## 🔧 技术架构

### 三客户端系统

机器人同时运行三个Telegram客户端：

1. **bot** (Telethon) - 主机器人客户端，用于事件处理和大文件上传
2. **userbot** (Pyrogram) - 用户会话客户端，用于访问受限频道
3. **Bot** (Pyrogram) - 辅助机器人客户端，用于Pyrogram特定操作

### 插件系统

插件自动从`main/plugins/`目录加载：
- `main/__main__.py`使用glob发现所有`.py`文件
- `main/utils.py:load_plugins()`动态导入每个插件
- 插件使用Telethon/Pyrogram的装饰器注册事件处理器

### 核心消息流程

1. 用户发送消息链接 → `frontend.py`或`start.py`处理请求
2. 链接解析 → `helpers.py:get_link()`提取chat_id和msg_id
3. 消息获取 → `pyroplug.py:get_msg()`从源频道下载
4. 流量检查 → `database.py:check_traffic_limit()`验证用户配额
5. 上传给用户 → 根据媒体类型/大小使用Pyrogram或Telethon
6. 清理 → 下载的文件在上传后被删除

### 文件上传策略 (`pyroplug.py:get_msg()`)

实现回退逻辑：
- 首先尝试Pyrogram上传
- 失败时回退到Telethon的`fast_upload`处理大文件或错误
- 针对视频笔记、视频、照片、文档的不同处理
- 使用ethon库自动提取元数据

### 数据库系统

**MongoDB数据库** (`main/database.py`) - 所有数据存储必需：
- **users**: user_id, username, is_banned, join_date, last_used
- **download_history**: message_id, chat_id, media_type, file_size, status
- **user_stats**: total_downloads, total_size per user
- **batch_tasks**: 批量操作进度跟踪
- **user_traffic**: 每日/每月/累计上传/下载统计
- **traffic_limits**: 全局流量限制配置
- **settings**: 流量限制配置

### 任务队列和速率限制 (`main/queue_manager.py`)

三组件系统：
1. **TaskQueue**: 异步队列，3个并发工作者处理并行任务
2. **RateLimiter**: 令牌桶算法实现平滑速率控制
3. **AdaptiveRateLimiter**: 根据Telegram响应自动调整速率
   - 初始速率：0.5请求/秒
   - 范围：0.1 - 10请求/秒
   - 突发：3个令牌
   - 遇到FloodWait：速率降低50%
   - 连续10次成功后：速率提高20%

---

## 📊 流量管理

默认限制（可通过`/setlimit`命令配置）：
- 每日限制：1GB/用户
- 每月限制：10GB/用户
- 单文件限制：100MB
- 默认启用

流量在每次下载前检查：
- 从消息元数据获取文件大小
- 调用`db.check_traffic_limit(sender, file_size)`
- 超过配额时拒绝下载并显示信息
- 成功上传后记录流量

---

## 🛡️ 安全特性

- SESSION字符串加密存储（可选）
- 用户访问控制（仅授权用户可使用）
- 流量限制防止滥用
- 自适应速率限制避免被Telegram限制
- 错误处理和日志记录

---

## 📈 性能优化

- 异步处理提高并发能力
- 自适应速率限制优化请求频率
- 连接池管理减少资源消耗
- 内存优化避免内存泄漏
- 批量下载提高效率

---

## 🤝 贡献

欢迎提交Issue和Pull Request来改进项目！

---

## 📄 许可证

本项目基于MIT许可证开源。