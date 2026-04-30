# AGENTS.md - TG Content Bot Pro

## 入口命令

```bash
python -m main
```

或直接在项目根目录运行：
```bash
python3 -m main
```

## 环境配置

- 必需的环境变量：`API_ID`, `API_HASH`, `BOT_TOKEN`, `AUTH`, `MONGO_DB`
- 项目会自动从 `.env` 文件加载环境变量（通过 `decouple` 库）
- 配置文件参考：`.env.example`

## 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python -m main
```

## Docker 开发

```bash
# 构建并运行
docker-compose up -d --build

# 或使用预构建镜像
docker run -d --name tg-content-bot-pro --env-file .env -p 28089:28089 ghcr.io/liwoyuandiane/tg-content-bot-pro:latest
```

## CI/CD

GitHub Actions 自动构建 Docker 镜像并推送到 GHCR：
- 推送到 `main` 分支或打 `v*` 标签时触发
- 多平台构建：linux/amd64, linux/arm64

## 项目结构

- `main/` - 核心代码目录
- `main/app.py` - 应用主入口
- `main/config.py` - 配置管理
- `main/handlers.py` - 消息处理器
- `main/core/` - 核心逻辑
- `main/services/` - 服务层
- `main/utils/` - 工具函数

## 注意事项

- 无正式测试框架
- 无 lint/typecheck 配置
- MongoDB 为必需依赖（用于会话持久化）
- SESSION 字符串用于访问私有频道/群组
- 公开群组消息转发失败时直接提示用户