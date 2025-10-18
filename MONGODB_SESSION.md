# MongoDB SESSION 管理功能

## 功能概述

现在支持通过 MongoDB 动态管理 SESSION 字符串，无需重新部署即可添加/删除/切换 SESSION。

## 配置 MongoDB

### 环境变量

在 `.env` 文件中添加：

```bash
# MongoDB 连接字符串
MONGO_URI=mongodb://localhost:27017/tg_content_bot

# 或使用 MongoDB Atlas（推荐）
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/tg_content_bot
```

### MongoDB Atlas 免费版

1. 访问 https://www.mongodb.com/cloud/atlas
2. 注册并创建免费集群（512MB 存储）
3. 创建数据库用户和密码
4. 获取连接字符串
5. 将连接字符串填入 `MONGO_URI`

## SESSION 管理命令

### /addsession - 添加 SESSION

```bash
/addsession <session_string>
```

**示例：**
```
/addsession AQFLdDsAXlVEomZqU2Ys-T1Ir0UpWGu...
```

**说明：**
- 将 SESSION 字符串保存到 MongoDB
- 重启机器人后自动加载
- 支持多用户（每个用户有自己的 SESSION）

### /delsession - 删除 SESSION

```bash
/delsession
```

**说明：**
- 删除当前用户的 SESSION
- 重启后恢复使用环境变量中的 SESSION（如果有）

### /sessions - 查看所有 SESSION

```bash
/sessions
```

**示例输出：**
```
📋 已保存的 SESSION 列表

1. 用户: @username (5350584287)
   SESSION: AQFLdDsAXlVEomZqU2...

总计: 1 个会话
```

### /mysession - 查看自己的 SESSION

```bash
/mysession
```

**示例输出：**
```
🔐 您的 SESSION 信息

用户ID: 5350584287
SESSION: AQFLdDsAXlVEomZqU2Ys-T1Ir...

⚠️ 请勿泄露此信息
```

## 使用流程

### 方式 1：MongoDB 管理（推荐）

1. **配置 MongoDB**：
   ```bash
   # .env
   MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/tg_bot
   ```

2. **启动机器人**（不需要 SESSION）：
   ```bash
   python3 -m main
   ```

3. **通过机器人添加 SESSION**：
   ```
   /addsession <session_string>
   ```

4. **重启机器人**，自动加载 SESSION

### 方式 2：环境变量（传统方式）

1. **配置 .env**：
   ```bash
   SESSION=your_session_string_here
   ```

2. **启动机器人**：
   ```bash
   python3 -m main
   ```

### 方式 3：混合模式

- 环境变量中配置默认 SESSION
- MongoDB 中可覆盖或添加新 SESSION
- 优先使用 MongoDB 中的 SESSION

## 启动逻辑

机器人启动时按以下顺序查找 SESSION：

1. **检查 MongoDB** → 如果配置了 `MONGO_URI` 且有保存的 SESSION，使用 MongoDB 的
2. **使用环境变量** → 如果 MongoDB 没有，使用 `.env` 中的 `SESSION`
3. **无 SESSION 模式** → 如果都没有，以有限功能运行（无法访问受限内容）

**启动日志示例：**
```
✅ 从 MongoDB 加载 SESSION
✅ Userbot 启动成功
```

或

```
⚠️ 未配置 SESSION，机器人将以有限功能运行
使用 /addsession 命令添加 SESSION（需要 MongoDB）
```

## 数据库结构

### users 集合

```javascript
{
  "user_id": 5350584287,
  "username": "your_username",
  "first_name": "Your Name",
  "session_string": "AQFLdDsAXlVE...",
  "session_updated": ISODate("2025-10-18T10:30:00Z"),
  "join_date": ISODate("2025-10-18T09:00:00Z"),
  "is_banned": false,
  "daily_upload": 0,
  "daily_download": 1048576,
  "monthly_upload": 0,
  "monthly_download": 10485760,
  "total_upload": 0,
  "total_download": 104857600
}
```

### settings 集合

```javascript
{
  "type": "traffic_limits",
  "daily_limit": 1073741824,
  "monthly_limit": 10737418240,
  "per_file_limit": 104857600,
  "enabled": 1
}
```

## 优势

### 相比传统方式

**传统方式（环境变量）：**
- ❌ 修改 SESSION 需要重新部署
- ❌ 无法动态切换账号
- ❌ SESSION 暴露在配置文件中

**MongoDB 方式：**
- ✅ 无需重新部署，机器人内直接管理
- ✅ 支持多用户多 SESSION
- ✅ SESSION 加密存储在数据库
- ✅ 可以随时添加/删除/查看
- ✅ 流量数据同步存储

## 安全建议

1. **保护 MongoDB 连接字符串**
   - 不要将 `MONGO_URI` 提交到 Git
   - 使用 IP 白名单限制访问

2. **保护 SESSION 字符串**
   - 不要在公开频道发送 SESSION
   - 定期更换 SESSION

3. **使用 MongoDB Atlas**
   - 启用用户认证
   - 使用强密码
   - 启用网络访问控制

## 故障排查

### MongoDB 连接失败

```
MongoDB 连接失败: [Error details]
```

**解决：**
- 检查 `MONGO_URI` 格式
- 检查网络连接
- 检查 MongoDB 服务状态

### SESSION 无效

```
⚠️ Userbot 启动失败: [Error details]
```

**解决：**
- 重新生成 SESSION：`python3 get_session.py`
- 使用 `/addsession` 更新 SESSION
- 检查 SESSION 字符串完整性

### 降级运行

```
⚠️ 未配置 SESSION，机器人将以有限功能运行
```

**影响：**
- ✅ 可以使用基本命令
- ✅ 可以管理流量限制
- ❌ 无法访问受限频道内容
- ❌ 无法下载私密频道消息

## 迁移指南

### 从环境变量迁移到 MongoDB

1. **配置 MongoDB**：
   ```bash
   MONGO_URI=your_mongodb_uri
   ```

2. **保留现有 SESSION**（可选）：
   ```bash
   SESSION=your_session_string  # 作为备份
   ```

3. **通过机器人添加**：
   ```
   /addsession <your_session_string>
   ```

4. **验证**：
   ```
   /mysession  # 查看是否保存成功
   ```

5. **删除环境变量**（可选）：
   ```bash
   SESSION=  # 留空
   ```

## 示例场景

### 场景 1：多账号管理

```bash
# 用户 A 添加自己的 SESSION
用户A: /addsession AAABBBCCCxxx...

# 用户 B 添加自己的 SESSION  
用户B: /addsession DDDEEEFFFyyy...

# 查看所有 SESSION
管理员: /sessions

# 输出：
# 1. 用户A (123456) - SESSION: AAABBBCCCxxx...
# 2. 用户B (789012) - SESSION: DDDEEEFFFyyy...
```

### 场景 2：SESSION 轮换

```bash
# 删除旧 SESSION
/delsession

# 添加新 SESSION
/addsession <new_session_string>

# 重启机器人
# 自动加载新 SESSION
```

### 场景 3：应急回退

```bash
# MongoDB 故障时
# 机器人自动使用环境变量中的 SESSION
# 或以无 SESSION 模式运行

# 恢复后重新添加
/addsession <session_string>
```

## 常见问题

**Q: MongoDB 是必需的吗？**
A: 不是。可以继续使用环境变量中的 SESSION。MongoDB 只是提供了更灵活的管理方式。

**Q: 可以同时使用多个 SESSION 吗？**
A: 目前每个用户一个 SESSION。机器人启动时只加载所有者的 SESSION。

**Q: SESSION 存储安全吗？**
A: SESSION 以明文存储在 MongoDB。建议：
- 使用 MongoDB Atlas 的加密连接
- 配置 IP 白名单
- 使用强密码

**Q: 不配置 MongoDB 会怎样？**
A: 机器人正常运行，但无法使用 SESSION 管理命令。必须通过环境变量配置 SESSION。

**Q: 流量统计也存在 MongoDB 吗？**
A: 是的。如果配置了 MongoDB，流量数据会存储在 MongoDB；否则使用 SQLite。
