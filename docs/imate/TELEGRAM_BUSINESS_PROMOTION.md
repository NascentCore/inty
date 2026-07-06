# 用 Telegram promotion program 推广 iMate companion bot

> 本文由 AI agent 整体生成。
> 读者：负责 Telegram 增长投放的人类队友，以及确认现有 Telegram onboard 链路是否可直接推广的后端工程师。
> 写作原则（minimal）：只写关键指令，不写 Telegram UI 里一望即知的点按步骤。

## Overall setup

当前只需要在 Telegram promotion program / Telegram ads 里直接推广 companion bot onboard URL：

```text
https://t.me/inty_official_bot?start=onboard
```

```overall-setup
[Telegram promotion program]
        |
        v
https://t.me/inty_official_bot?start=onboard
        |
        v
[iMate companion bot]  --/start onboard-->  bootstrap  -->  1 user : 1 Inty bond
```

一句话心智：**promotion program 负责带来点击，existing Telegram onboard 负责建立关系**。
这与 [companion_harness/DESIGN.md](/docs/imate/companion_harness/DESIGN.md) 的 Channels 立场一致：Telegram 是 relationship 的 manifestation surface，关系本身由 companion harness 承载。

## Current launch path（不需要额外 feature development）

- 投放 URL 固定使用 `https://t.me/inty_official_bot?start=onboard`。
- 这条链接对应现有 Ops Telegram onboard：`/start onboard` 会自动 provisioning guest user + PRIVATE agent，并进入 bootstrap。
- 当前投放不需要新的 bot、landing page、attribution 参数或 Telegram channel code。

## Ad copy（user-facing language = English）

目标用户为英文使用者。Telegram promotion program 里的标题、描述、CTA 只用 English。

可直接使用的文案：

```text
Meet an AI companion who remembers you.
Start your Inty on Telegram.
```

备选：

```text
Your Inty is an AI companion built just for you —
it remembers, checks in, and grows with you over time.
```

## Preflight check（投放前只查关键项）

- 打开 `https://t.me/inty_official_bot?start=onboard`，确认会进入 `@inty_official_bot` 并显示 Start。
- 点击 Start，确认 bot 收到 `/start onboard` 后进入 iMate onboarding / bootstrap。
- 确认 bot profile 的 name / description / avatar 面向 English speaker，避免广告点击后的落差。
- 确认 Ops Telegram channel 正在运行并使用 `inty_official_bot` 的 token；配置入口见 `resolved_telegram_bot_token`（[app/utils/config.py](/app/utils/config.py)）。

## Measurement（只看主漏斗）

- Telegram promotion program 自带：impression、click、spend。
- Inty 侧：`agent_channel_endpoints` 新增绑定数；debug 查看 `GET /api/v1/telegram/debug/bindings`。
- 产品北极星：点击 → `/start onboard` → bootstrap 完成 → 次周回访（retention），见 [docs/imate/DESIGN.md](/docs/imate/DESIGN.md) 与 [companion_harness/DESIGN.md](/docs/imate/companion_harness/DESIGN.md)。

## See also

- 仓库内：[docs/imate/DESIGN.md](/docs/imate/DESIGN.md)、[docs/imate/COMMERCIALIZATION.md](/docs/imate/COMMERCIALIZATION.md)、[docs/imate/companion_harness/DESIGN.md](/docs/imate/companion_harness/DESIGN.md)（Channels 节）、[docs/imate/USER_MANUAL.md](/docs/imate/USER_MANUAL.md)。
- 代码锚点：[backend/ops/telegram_channel/binding.py](/backend/ops/telegram_channel/binding.py)、[backend/ops/telegram_channel/transport.py](/backend/ops/telegram_channel/transport.py)、[app/services/agentic_channel/provision.py](/app/services/agentic_channel/provision.py)。
- 外部：[Bot Features / Deep Linking](https://core.telegram.org/bots/features)、[Deep links 规范](https://core.telegram.org/api/links)。
