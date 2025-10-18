# 流量监控功能说明

## 功能概述

已为机器人添加完整的流量监控和限制功能，适合部署在云平台避免流量超额。

## 默认配置

```
📅 每日流量限制: 1GB / 用户
📆 每月流量限制: 10GB / 用户  
📄 单文件大小限制: 100MB
🟢 状态: 已启用
```

## 用户命令

### /traffic - 查看个人流量统计
查看自己的流量使用情况，包括：
- 今日上传/下载
- 本月上传/下载
- 累计上传/下载
- 剩余流量

示例输出：
```
📊 个人流量统计

今日使用：
📥 下载: 245.67 MB
📤 上传: 245.67 MB

本月使用：
📥 下载: 3.21 GB
📤 上传: 3.21 GB

累计使用：
📥 下载: 15.78 GB
📤 上传: 15.78 GB

流量限制： 🟢 已启用
📅 日限额: 1.00 GB
   剩余: 754.33 MB
📆 月限额: 10.00 GB
   剩余: 6.79 GB
📄 单文件限制: 100.00 MB
```

## 管理员命令（仅所有者）

### /totaltraffic - 查看总流量统计
查看所有用户的流量汇总：
- 今日总下载量
- 本月总下载量
- 累计总上传/下载
- 当前限制配置

### /setlimit - 设置流量限制

**用法：**
```bash
/setlimit daily <数值>     # 设置日限额(MB)
/setlimit monthly <数值>   # 设置月限额(GB)
/setlimit file <数值>      # 设置单文件限制(MB)
/setlimit enable           # 启用流量限制
/setlimit disable          # 禁用流量限制
```

**示例：**
```bash
/setlimit daily 1024       # 设置日限额 1GB
/setlimit monthly 10       # 设置月限额 10GB
/setlimit file 100         # 单文件最大 100MB
/setlimit disable          # 禁用流量限制（不限流量）
```

### /resettraffic - 重置流量统计

**用法：**
```bash
/resettraffic daily        # 重置所有用户今日流量
/resettraffic monthly      # 重置所有用户本月流量
/resettraffic all          # 重置所有流量统计
```

## 流量限制说明

### 自动检查
- 下载前自动检查文件大小和剩余流量
- 超限时拒绝下载并提示用户
- 自动记录上传和下载流量

### 自动重置
- 每日流量：每天 00:00 自动重置
- 月流量：每月 1 日 00:00 自动重置
- 累计流量：不会自动重置

### 限制生效
当用户超过限制时：
```
❌ 今日流量不足，剩余 123.45 MB

使用 /traffic 查看流量使用情况
```

## 云平台部署建议

### 低流量配置（免费套餐）
适合 Railway/Render 免费版：
```bash
/setlimit daily 500        # 日限额 500MB
/setlimit monthly 5        # 月限额 5GB
/setlimit file 50          # 单文件 50MB
```

### 中等流量配置
适合付费套餐：
```bash
/setlimit daily 2048       # 日限额 2GB
/setlimit monthly 20       # 月限额 20GB
/setlimit file 200         # 单文件 200MB
```

### 无限流量配置
如果不担心流量：
```bash
/setlimit disable          # 完全禁用流量限制
```

## 数据库表结构

### user_traffic 表
记录每个用户的流量使用：
- daily_upload/download - 今日上传/下载
- monthly_upload/download - 本月上传/下载
- total_upload/download - 累计上传/下载
- last_reset_daily/monthly - 最后重置时间

### traffic_limits 表
全局流量限制配置：
- daily_limit - 日限额（字节）
- monthly_limit - 月限额（字节）
- per_file_limit - 单文件限额（字节）
- enabled - 是否启用限制

## 流量计算

- **下载流量**：从 Telegram 下载到服务器的流量
- **上传流量**：从服务器上传到用户的流量
- **计费流量**：下载 + 上传（当前实现为相同值）

## 监控建议

1. **定期检查总流量**
   ```bash
   /totaltraffic
   ```

2. **每日查看使用情况**
   ```bash
   /traffic
   ```

3. **及时调整限制**
   根据云平台实际流量使用情况调整限制

4. **月初重置**
   如需重置月流量统计：
   ```bash
   /resettraffic monthly
   ```

## 注意事项

1. 流量统计在文件上传成功后才记录
2. 下载失败不计入流量
3. 文本消息不计入流量
4. 流量数据存储在 SQLite 数据库中
5. 重置操作不可恢复，请谨慎使用

## 云平台流量限制参考

| 平台 | 免费流量/月 | 建议配置 |
|------|------------|---------|
| Railway | 100GB | 月限 5-8GB/用户 |
| Render | 100GB | 月限 5-8GB/用户 |
| Koyeb | 无限 | 可不限制 |
| Zeabur | 看套餐 | 根据套餐调整 |

## 故障排查

**问题：流量统计不准确**
```bash
/resettraffic all          # 重置统计
```

**问题：误触发流量限制**
```bash
/setlimit daily 10240      # 临时提高限额
# 或
/setlimit disable          # 临时禁用限制
```

**问题：需要清空历史数据**
直接删除数据库文件：
```bash
rm bot_data.db
# 重启机器人会自动重建数据库
```
