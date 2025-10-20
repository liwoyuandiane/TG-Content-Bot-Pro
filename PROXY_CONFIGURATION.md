# 代理配置指南

本项目支持 SOCKS5 和 HTTP 代理配置，以解决网络连接问题。

## 支持的代理类型

1. **SOCKS5 代理** - 推荐使用，支持用户名/密码认证
2. **HTTP 代理** - 支持用户名/密码认证

## 环境变量配置

在 `.env` 文件中添加以下配置：

### SOCKS5 代理配置示例

```bash
# 代理协议 (socks5, socks4, http, https)
TELEGRAM_PROXY_SCHEME=socks5

# 代理服务器地址
TELEGRAM_PROXY_HOST=154.201.86.151

# 代理端口
TELEGRAM_PROXY_PORT=38512

# 代理认证信息（可选）
TELEGRAM_PROXY_USERNAME=Ue9h0D55LS
TELEGRAM_PROXY_PASSWORD=CaqlJmzRWc
```

### HTTP 代理配置示例

```bash
# 代理协议
TELEGRAM_PROXY_SCHEME=http

# 代理服务器地址
TELEGRAM_PROXY_HOST=154.201.86.151

# 代理端口
TELEGRAM_PROXY_PORT=19496

# 代理认证信息（可选）
TELEGRAM_PROXY_USERNAME=wCBcuVZXd6
TELEGRAM_PROXY_PASSWORD=XM1Xdwey02
```

## 配置说明

- `TELEGRAM_PROXY_SCHEME`: 代理协议类型 (socks5, socks4, http, https)
- `TELEGRAM_PROXY_HOST`: 代理服务器地址
- `TELEGRAM_PROXY_PORT`: 代理服务器端口
- `TELEGRAM_PROXY_USERNAME`: 代理用户名（可选）
- `TELEGRAM_PROXY_PASSWORD`: 代理密码（可选）

## 使用建议

1. **优先使用 SOCKS5 代理**：SOCKS5 代理在 Pyrogram 和 Telethon 中都有更好的支持
2. **认证信息可选**：如果代理不需要认证，可以不设置用户名和密码
3. **测试连接**：配置完成后，启动机器人测试代理是否正常工作

## 故障排除

如果代理配置后仍然无法连接：

1. 检查代理服务器地址和端口是否正确
2. 验证用户名和密码是否正确
3. 确认代理服务器是否正常工作
4. 查看日志文件获取更多错误信息
5. 尝试使用不同的代理类型