# SOCKS5代理配置解决方案



## 解决方案

### 方案1: 使用SOCKS5代理（推荐）

1. **部署SOCKS5代理服务器**：
   - 在VPS或云服务器上部署SOCKS5代理
   - 配置服务器只允许连接到Telegram服务器
   - 使用强密码保护代理服务器

2. **配置.env文件**：
   ```bash
   # SOCKS5代理设置（替代HTTP代理）
   # TELEGRAM_PROXY_SCHEME=socks5
   # TELEGRAM_PROXY_HOST=your-socks5-proxy-server.com
   # TELEGRAM_PROXY_PORT=1080
   ```

### 方案2: 使用传统的HTTP代理

1. **部署支持HTTP CONNECT的代理服务器**：
   - 使用Squid、Nginx或其他支持HTTP CONNECT的代理服务器
   - 配置只允许连接到Telegram服务器
   - 部署在支持CONNECT方法的平台上

2. **配置.env文件**：
   ```bash
   # HTTP代理设置
   TELEGRAM_PROXY_SCHEME=http
   TELEGRAM_PROXY_HOST=your-http-proxy-server.com
   TELEGRAM_PROXY_PORT=8080
   ```

### 方案3: 直接连接（如果网络允许）

如果您的网络环境可以直接访问Telegram服务器，可以禁用代理：

```bash
# 注释掉或删除代理配置
# TELEGRAM_PROXY_SCHEME=
# TELEGRAM_PROXY_HOST=
# TELEGRAM_PROXY_PORT=
```

## 推荐的SOCKS5代理部署方案

### 使用Dante Server部署SOCKS5代理

1. **安装Dante Server**：
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install dante-server
   
   # CentOS/RHEL
   sudo yum install dante-server
   ```

2. **配置Dante Server** (`/etc/dante.conf`)：
   ```conf
   logoutput: syslog
   user.privileged: root
   user.unprivileged: nobody
   
   # 服务器监听地址
   internal: 0.0.0.0 port=1080
   
   # 外部接口
   external: eth0
   
   # 授权方法
   method: username none
   
   # 用户认证（可选）
   userlist {
       user: telegram uid 1000
   }
   
   # 只允许连接到Telegram服务器
   pass {
       from: 0.0.0.0/0 to: 149.154.160.0/22
       command: connect
   }
   pass {
       from: 0.0.0.0/0 to: 91.108.56.0/22
       command: connect
   }
   
   # 拒绝其他连接
   block {
       from: 0.0.0.0/0 to: 0.0.0.0/0
       log: connect error
   }
   ```

3. **启动服务**：
   ```bash
   sudo systemctl start danted
   sudo systemctl enable danted
   ```

## 本地测试脚本

使用以下脚本测试代理连接：

```bash
# 测试SOCKS5代理
curl --socks5 your-proxy-server:1080 https://api.telegram.org

# 测试HTTP代理
curl --proxy http://your-proxy-server:8080 https://api.telegram.org
```

## 安全建议

1. **限制连接目标**：只允许连接到Telegram服务器IP范围
2. **使用强密码**：为代理服务器设置强密码
3. **定期更新**：保持代理服务器软件更新
4. **日志监控**：监控代理服务器日志以检测异常活动
5. **防火墙配置**：只开放必要的端口

## 结论

建议使用SOCKS5代理或其他支持CONNECT方法的代理服务器来解决Telegram连接问题。