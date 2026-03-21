# Telegram Perpetual Agent 路演脚本（5 分钟）

## 目标

- 在投资人自己的 Telegram 上，实时展示与 perpetual agent 的多轮对话能力。
- 展示闭环：`Telegram 消息 -> Agent 处理 -> Telegram 回复`。

---

## 0) 演示前准备（2 分钟）

### A. Bot 与会话准备

1. 使用 `@BotFather` 创建 Bot，拿到 Bot Token。
2. 将 Bot 链接发给投资人（`https://t.me/<your_bot_username>`）。
3. 请投资人点击 `Start`，并发送一条测试消息（例如 `Hi`）。

**最小校验 token（可选）：** 在终端执行（勿把 token 贴进聊天记录或提交到 git）：

```bash
curl -sS "https://api.telegram.org/bot<你的bot_token>/getMe"
```

期望返回 `"ok":true` 且 `result.username` 为你的 bot 用户名。详见 [Bot API getMe](https://core.telegram.org/bots/api#getme)。

### B. 本地启动命令（仓库根目录）

```bash
export TELEGRAM_BOT_TOKEN="<你的bot token>"
export TELEGRAM_CHAT_ID="<投资人的chat_id>"

python -m experimental.perpetual_agent.main \
  --mode living \
  --telegram \
  --telegram-max-user-turns 200 \
  --proactive-interval-seconds 60
```

> 推荐固定 `TELEGRAM_CHAT_ID`，避免其他 Telegram 用户串场消息。

---

## 1) 现场演示脚本（按时间轴）

### 00:00 - 00:40 开场

**你说：**

> “现在我本地运行的是一个持续运行的 AI companion。它通过 Telegram 和用户实时沟通。您可以直接在自己的 Telegram 给这个 Bot 发消息。”

**你做：**

- 展示终端中的运行命令与运行状态（进程保持运行）。

### 00:40 - 02:30 核心交互（投资人发起）

**你说：**

> “请您发一条：`我今晚有点焦虑，帮我规划明天。`”

**你做：**

1. 让投资人发送该消息。
2. 同时展示：
   - Telegram 对话窗口中 Bot 的回复；
   - 终端里对应的 `telegram_user_turn` 日志行。

**你补充一句：**

> “这里不是预录，终端会实时打印每一轮 turn 的处理结果。”

### 02:30 - 03:30 多轮持续对话

**你说：**

> “请再发一条：`请继续在 telegram 跟我聊，给我三个可执行建议。`”

**你做：**

- 展示 Bot 连续回复，强调这是同一会话上下文中的连续多轮。

### 03:30 - 04:30 主动触达演示

**你说：**

> “如果用户一段时间没有输入，agent 会主动关怀。”

**你做：**

- 等待约 60 秒（前面命令已设置 `--proactive-interval-seconds 60`）。
- 展示 Telegram 中 Bot 主动发出的消息。

### 04:30 - 05:00 收尾

**你说：**

> “这就是一个完整闭环：用户在 Telegram 发消息，perpetual agent 持续理解并回复，并且可在沉默期主动触达。”

---

## 2) 主持人备注（防翻车）

1. **强烈建议固定 chat_id**
   - 否则可能收到其他用户消息，影响演示稳定性。
2. **`TELEGRAM_CHAT_ID` 必须与投资人账号一致**
   - 若写错（占位符、他人 id、非数字私聊 id），程序会**忽略**投资人发来的消息，且可能在 **proactive** 时 `sendMessage` 返回 **HTTP 400** 直接崩溃。
   - 彩排时若不确定 id：可先 `unset TELEGRAM_CHAT_ID`，不传 `--telegram-chat-id`，由**第一条收到的文本消息**自动绑定 chat；确认无误后再在正式路演中改为固定 `TELEGRAM_CHAT_ID`。
3. **进程必须常驻**
   - Telegram 上消息显示双勾只表示送达服务器，不代表本机 agent 仍在运行；演示全程保持终端进程不退出。
4. **将 user turns 上限调大**
   - `--telegram-max-user-turns 200` 可避免中途因默认上限退出。
5. **提前做一次彩排**
   - 至少提前 5 分钟发 2 条测试消息，确认网络与 token 正常。可对照仓库 [tests/docs/TEST_STEPS_TELEGRAM_PERPETUAL_AGENT.md](/tests/docs/TEST_STEPS_TELEGRAM_PERPETUAL_AGENT.md)。

---

## 3) 30 秒应急预案

### 情况 A：投资人发了消息但 Bot 不回

- 检查投资人是否已点击 `Start`。
- 检查 `TELEGRAM_BOT_TOKEN` 是否正确（可用本节 A 的 `curl getMe`）。
- 若设置了 `TELEGRAM_CHAT_ID` / `--telegram-chat-id`，核对是否为投资人的**数字** chat id；错误时先 `unset TELEGRAM_CHAT_ID` 后重启，让第一条消息自动绑定。
- 观察终端是否有异常报错（例如 `HTTP Error 400` 多与错误 chat_id 有关）并立刻重启命令。

### 情况 B：Bot 回错人或消息混乱

- 立即重启并显式设置 `TELEGRAM_CHAT_ID` 为投资人 chat_id。

### 情况 C：演示中进程自动退出

- 增大 `--telegram-max-user-turns` 后重启。

---

## 4) 建议投资人体验的三条示例提问

1. `我现在很焦虑，帮我做一个明天上午的 3 步计划。`
2. `把刚才建议压缩成 3 条可执行 TODO。`
3. `如果我今晚睡不着，你会怎么提醒我放松？`

