# TEST_STEPS_TELEGRAM_PERPETUAL_AGENT

## 目标

验证 `experimental.perpetual_agent` 在 **Telegram 长轮询** 模式下端到端可用：

1. Bot token 有效（`getMe`）
2. 本地进程持续运行时，用户在 Telegram 发文本 → 终端出现 `telegram_user_turn` → Bot 在同一会话回复

## 前置条件

- 已通过 `@BotFather` 创建 bot，并已取得 `TELEGRAM_BOT_TOKEN`
- 在 Telegram 中打开该 bot，至少点击一次 **Start**（私聊场景常规要求）
- 仓库根目录可执行 `uv run python`（或等价的 `python` + 依赖环境）

## 步骤 1：验证 token（可选但推荐）

```bash
curl -sS "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe"
```

**通过标准：** JSON 中 `"ok": true`，且 `result.username` 与 bot 一致。

## 步骤 2：清空可能干扰的 chat_id

若曾设置过错误的 `TELEGRAM_CHAT_ID`（会导致忽略你的消息或 `sendMessage` 400），先取消：

```bash
unset TELEGRAM_CHAT_ID
```

## 步骤 3：启动 living + Telegram 模式

在仓库根目录：

```bash
export TELEGRAM_BOT_TOKEN="<your-bot-token>"

uv run python -m experimental.perpetual_agent.main \
  --mode living \
  --telegram \
  --telegram-max-user-turns 5 \
  --telegram-poll-timeout-seconds 20 \
  --proactive-interval-seconds 3
```

保持进程运行，不要退出终端。

## 步骤 4：在 Telegram 发消息

向该 bot 发送一条纯文本，例如：`Hello`

## 通过标准

- 终端出现一行类似：`[telegram_user_turn step=1] channel=telegram model=fast-text-1 ... msg=[fast-text-1] via telegram | ... | I heard you: Hello`
- Telegram 对话中出现 bot 回复，正文为 **脚本模板**（含 `I heard you:` 与你的输入），与终端 `msg=` 一致

## 已知说明

- 演示使用 `ScriptedModelExecutor`，非真实大模型对话。
- 双勾仅表示消息送达 Telegram，不代表本进程仍在运行或已处理；进程崩溃或错误 `chat_id` 时可能无回复。

## 相关文档

- [experimental/perpetual_agent/README.md](/experimental/perpetual_agent/README.md)
- [ROAD_SHOW_SCRIPT.md](/ROAD_SHOW_SCRIPT.md)（路演场景与固定 `TELEGRAM_CHAT_ID` 建议）
