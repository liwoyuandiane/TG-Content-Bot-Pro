# Cloudflare Workers 部署说明

## 部署步骤

1. 访问 [Cloudflare Workers](https://workers.cloudflare.com/) 并登录
2. 点击 "Create a Worker"
3. 将 `cloudflare-worker.js` 文件中的代码复制到编辑器中
4. 点击 "Save and Deploy"

## 使用方法

部署完成后，你会得到一个类似 `https://your-worker.your-account.workers.dev` 的 URL。

在你的 `.env` 文件中添加以下环境变量：

```bash
# 使用 Cloudflare Workers 代理 Telegram API
TELEGRAM_API_URL=https://your-worker.your-account.workers.dev
```

## 配置说明

如果你需要自定义路由，可以在 Cloudflare 仪表板中：

1. 进入 Workers 页面
2. 选择你刚刚创建的 Worker
3. 点击 "Add route"
4. 设置路由模式，例如 `tgapi.yourdomain.com/*`
5. 选择你创建的 Worker

这样你就可以使用自定义域名来访问 Telegram API 代理了。