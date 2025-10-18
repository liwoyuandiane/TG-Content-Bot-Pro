# SESSION 生成指南

## 方法一：使用交互式脚本（推荐）

### 步骤：

1. **SSH 连接到服务器**
   ```bash
   ssh 您的服务器地址
   ```

2. **进入项目目录**
   ```bash
   cd /root/TG-Content-Bot-Pro
   source venv/bin/activate
   ```

3. **运行交互式生成器**
   ```bash
   python3 interactive_session.py
   ```

4. **按提示操作**
   - 输入手机号（例如：`+16828004917`）
   - 等待验证码（检查 Telegram 应用）
   - 输入验证码（例如：`1 2 3 4 5` 或 `12345`）
   - 如有两步验证，输入密码

5. **复制 SESSION 字符串**
   - 脚本会显示生成的 SESSION
   - 复制整个字符串

6. **保存到 .env 文件**
   ```bash
   nano /root/TG-Content-Bot-Pro/.env
   ```
   
   找到 `SESSION=` 这行，粘贴字符串：
   ```
   SESSION=你复制的SESSION字符串
   ```

7. **重启机器人**
   ```bash
   # 停止当前运行的机器人
   killall python3
   
   # 重新启动
   cd /root/TG-Content-Bot-Pro
   source venv/bin/activate
   python3 -m main
   ```

---

## 方法二：使用原始脚本

```bash
cd /root/TG-Content-Bot-Pro
source venv/bin/activate
python3 get_session.py
```

按提示输入：
1. API_ID: `21722171`
2. API_HASH: `6dc06adcb5961d617c347d7776d2ec76`
3. 手机号
4. 验证码

---

## 方法三：通过机器人命令（24小时后重试）

如果等待了足够长时间（24小时），验证码限制解除后：

1. 在 Telegram 中向机器人发送 `/generatesession`
2. 按提示操作
3. 查找验证码（Telegram 应用内）
4. 输入验证码

---

## 验证码查找位置

### Telegram 应用内验证码 (SentCodeType.APP)

**iOS/Android:**
- 通知栏
- Telegram 聊天列表顶部的 "Telegram" 账号
- 可能自动填充到输入框

**Desktop:**
- 系统通知
- Telegram 左侧联系人列表的 "Telegram" 账号

**Web:**
- 浏览器通知
- 聊天列表中的 "Telegram" 账号

---

## 常见问题

### Q1: 看不到验证码？
**A:** 
- 检查所有已登录的 Telegram 设备
- 查看系统通知设置
- 等待 1-2 小时后重试
- 使用其他手机号测试

### Q2: 提示 PHONE_CODE_EXPIRED？
**A:**
- 验证码已过期
- 重新运行脚本生成新的验证码

### Q3: 提示 SessionPasswordNeeded？
**A:**
- 您的账号启用了两步验证
- 需要输入两步验证密码

### Q4: 提示 FLOOD_WAIT？
**A:**
- 请求过于频繁
- 等待提示的时间（通常几小时到1天）

---

## 安全提示

⚠️ **重要**:
- SESSION 字符串等同于您的 Telegram 账号登录凭证
- 不要分享给任何人
- 定期更换 SESSION
- 不要上传到公开的代码仓库

---

## 技术支持

如遇问题，请检查：
1. API_ID 和 API_HASH 是否正确
2. 手机号格式是否正确（必须包含 + 和国家代码）
3. 网络连接是否正常
4. Python 环境是否正确激活

生成的诊断脚本可用于排查：
```bash
python3 final_diagnosis.py
python3 check_api.py
```
