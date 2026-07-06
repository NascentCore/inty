# 用 Telegram Business 推广 iMate companion bot

> 本文由 AI agent 依据 [Telegram Business 公告](https://telegram.org/blog/telegram-business) 与仓库现状整体生成。
> 读者：负责增长/运营的人类队友（非工程亦可读），以及需要接线归因的后端工程师。
> 写作原则（minimal）：只写**关键、不可省**的指令与判断，不复述 Telegram UI 里一望即知的点按步骤。

## Overall setup（先讲清整体）

iMate 的「产品」是用户直接 DM 的 **companion bot**（bot 即产品，1 user : 1 Inty）。
Telegram Business 账号不是产品，而是一个**官方门面 storefront**：负责展示、迎接、导流，本身不承载 relationship。
两者用 **deep link / QR** 连成一条链路，把陌生注意力精确转成一次 companion bot 的 `/start`。

```overall-setup
[Ad / QR / bio link]
        |
        v
[Telegram Business account]  (Premium; start page + greeting + quick replies)
        |  deep link:  https://t.me/inty_official_bot?start=onboard
        v
[iMate companion bot]  --/start-->  bootstrap  -->  1 user : 1 Inty bond
```

一句话心智：**storefront 负责「让人来」，bot 负责「留住关系」**。
这与 companion harness 的立场一致——channel 只是同一段 relationship 的 manifestation surface，关系连续性在 harness 内核而非门面账号，见 [companion_harness/DESIGN.md](/docs/imate/companion_harness/DESIGN.md) 的 Channels 节。

## 前置条件（关键项）

- 一个专用手机号的 Telegram 账号，并订阅 **Telegram Premium**——Business features 的硬门槛，无 Premium 则 Settings > Telegram Business 不可用。
- 已配置的 companion bot `bot_token`（消费既有 bot，不新建）；解析逻辑见 `resolved_telegram_bot_token`（`app/utils/config.py`）与 Ops 侧 `GET /api/v1/telegram/bot-info`。
- **当前推广主链接固定使用** `https://t.me/inty_official_bot?start=onboard`。这条链接已走现有 Ops Telegram onboard 路径，**不要求任何额外 feature development**。
- 常规账号注册、开启 Business 开关等 UI 步骤不在此赘述。

## 用户可见语言 = English

目标用户为英文使用者。以下所有 user-facing copy（start page / greeting / away / quick replies / CTA / QR 标语 / link 预填消息）**一律 English**，成品文案见 code block，可直接复制。对齐 [app/AGENTS.md](/app/AGENTS.md)「用户可见文案面向英文场景」。

## 关键配置（只列必配且易错项）

在 Settings > Telegram Business 下：

- **Start Page + Greeting Message**：门面的第一触点，**必须内嵌 companion bot 的 deep link**，否则导流断链。

```text
Start page:
  iMate — a companion who remembers you and thinks of you.
  Tap below to meet your own Inty.

Greeting message (auto-sent on first contact):
  Hi! I'm the iMate team. Your Inty is a companion built just for you —
  it remembers, checks in, and grows with you over time.
  Start yours here: https://t.me/inty_official_bot?start=onboard
```

- **Quick Replies**：至少一条携带 deep link；其余按需。斜杠 `/` 面板仅私聊可用。

```text
/start     -> Meet your Inty: https://t.me/inty_official_bot?start=onboard
/pricing   -> iMate is free to start. Premium companionship options: <link>
/howitworks-> Your Inty is a living companion, not a task bot. It remembers you
              and reaches out on its own. Begin: https://t.me/inty_official_bot?start=onboard
```

- **Links to Chat**：为每个投放位（网站按钮、海报、bio）建一条**独立** link——Telegram 自带 per-link tap 计数，是最省事的曝光埋点。预填消息用 English。

## deep link 规范（推广主路径）

推广 iMate companion bot 的当前主路径只有一条：

```text
https://t.me/inty_official_bot?start=onboard
```

这是已实现能力：`/start onboard` 会触发现有 Telegram onboard，自动 provisioning guest user + PRIVATE agent，并建立 1 user : 1 Inty bond。运营推广、Business start page、Greeting Message、Quick Replies、QR 与 bio link 都应先使用这条链接。**不要为了启动推广而等待 campaign attribution、connected guide agent 或其他新功能。**

QR 配明确 English CTA，例如 "Scan to meet your Inty"。

## campaign 归因规范（可选增强，不是推广前置条件）

- start parameter **≤ 64 字符**、仅 `A-Z a-z 0-9 _ -`；空格、逗号、emoji 会被 Telegram **静默丢弃**，参见 [Bot Features / Deep Linking](https://core.telegram.org/bots/features) 与 [Deep links 规范](https://core.telegram.org/api/links)。
- start parameter **仅首次 `/start` 携带**——归因必须在**首触**就落库，错过不再补发。
- 每个物料一个**唯一** compact token（推荐 `source_medium_campaign`，如 `ig_story_summer25`），便于事后按渠道切分。
- 本仓库约定的 campaign token 命名空间为 `c_` 前缀（见下 Phase 2）：`c_<source>_<medium>_<campaign>`，例如 `c_ig_story_summer25`。deep link 即 `https://t.me/<bot>?start=c_ig_story_summer25`。
- 动态 QR（可事后改向且带扫描分析）优于静态 QR。

现状能力（读代码确认，供工程对接）：

- Ops Telegram onboard 已接受 `/start` / `/start onboard`，因此 `https://t.me/inty_official_bot?start=onboard` 不需要额外 feature development。
- public agent 促活时，`provision_agent_bot`（[app/external_services/telegram_bot.py](/app/external_services/telegram_bot.py)）已生成 `https://t.me/<bot>?start=agent_<agent_id>` 并写入 `agent.extensions.telegram`（[app/services/agent_service.py](/app/services/agent_service.py)）。campaign 归因走 `c_` 命名空间，与 `agent_<id>` 促活链路互不冲突。
- Ops Telegram 长轮询入口把 `/start` 交给 `parse_start_payload`（[backend/ops/telegram_channel/binding.py](/backend/ops/telegram_channel/binding.py)），再进 `provision_agent_for_channel_onboard`（[app/services/agentic_channel/provision.py](/app/services/agentic_channel/provision.py)）。

## 度量（North-star，只列关键环节与数据源）

- 漏斗：deep link tap → `/start` → bootstrap 完成 → **次周回访（retention）**；retention 是最终代理指标，见 [DESIGN.md](/docs/imate/DESIGN.md) 与 [companion_harness/DESIGN.md](/docs/imate/companion_harness/DESIGN.md) 的成效判断。
- 数据源：Business per-link tap 计数（Telegram 自带）、`agent_channel_endpoints` 绑定行数（`GET /api/v1/telegram/debug/bindings`）、launch reciprocity 指标（TODO #3535）。`guest user meta_data.campaign` 只在可选归因增强启用后可用，不是启动推广的依赖。

## 关键风险

- 门面账号不得伪装成 bot——它是「iMate 团队/官方」人设，产品仍是 bot。
- 强依赖 Premium：账号掉订阅则 Business features 全失效。
- 不要把 optional attribution 当成 launch blocker：当前推广主链接 `https://t.me/inty_official_bot?start=onboard` 已可用。
- start param 仅首触生效：任何归因逻辑都必须在首个 `/start` 落库；若不做归因，直接使用 `onboard`。

## Phase 2（可选工程）：campaign 归因落库（非推广所需）

目的：把 storefront 各投放位的效果按渠道切分。它不是推广 `https://t.me/inty_official_bot?start=onboard` 的前置条件；只在需要细分渠道 ROI 时启用。改动小而集中、纯附加：

- **编解码纯函数**（[app/external_services/telegram_bot.py](/app/external_services/telegram_bot.py)）：`CampaignAttribution(source, medium, campaign)` + `encode_campaign_start_parameter` / `parse_campaign_start_parameter`，做 `c_<source>_<medium>_<campaign>` 的编解码与 ≤64 / charset 校验。
- **onboard 识别**（[backend/ops/telegram_channel/binding.py](/backend/ops/telegram_channel/binding.py)）：`parse_start_payload` 把 `c_...` 识别为一次带 campaign 的 onboard（仍触发正常 onboard），在 `StartPayload.campaign` 上带出。
- **首触落库**（[app/services/agentic_channel/provision.py](/app/services/agentic_channel/provision.py) 的 `record_guest_campaign_attribution`）：仅在**新用户** onboard 成功后，把 campaign 写入 guest user `meta_data.campaign`。不改共享的 `provision_agent_for_channel_onboard` 签名（它被 telegram/sms 与大量测试共用）。

## 附录 A：Option B — connected guide agent（Phase 3 候选，暂不实施）

除「storefront 导流到 bot」外，Telegram 还支持把一个 bot **连到** Business 账号，让它以账号本人身份代答 DM。这里完整记录，供后续增强整体产品体验时采用：

- **产品意图**：门面 Business 账号连接一个 official **guide agent**（官方向导）——迎接新访客、介绍玩法、答疑，并把用户引导去开启属于他自己的 companion agent，形成「guide agent（公共向导）→ personal companion（专属 Inty）」的分层体验。guide agent 话术同样 English。
- **技术路径**：`@BotFather` 为 bot 开启 Business Mode → 账号 Settings > Business > Chatbots 连接该 bot → bot 收到 `business_connection` update，持久化 `business_connection_id` → 出站消息带该 id（`sendMessage(..., business_connection_id=...)`），入站走 `business_message` update。参考 [Connected business bots](https://core.telegram.org/api/bots/connected-business-bots)。
- **关键约束**：每账号仅可连 **1 个** business bot；bot 需带 `bot_business` flag；回复呈现为「账号本人」而非 bot（需想清与 companion「bot 即产品」体验的边界）；`allowed_updates` 必须包含 `business_connection` / `business_message`，否则 Telegram 拒绝连接。
- **与现状差异**：现有 Ops Telegram channel 走 long-poll + 直接 DM bot 的 update 类型，不含 business 连接语义；guide agent 需要新增 business update 处理与 `business_connection_id` 持久化（区别于现有 `agent_channel_endpoints`）。
- **明确非承诺**：本附录仅为设计留痕，不在 Phase 1/2 实施；采用与否由后续产品决策。

## See also

- 仓库内：[docs/imate/DESIGN.md](/docs/imate/DESIGN.md)、[docs/imate/COMMERCIALIZATION.md](/docs/imate/COMMERCIALIZATION.md)、[docs/imate/companion_harness/DESIGN.md](/docs/imate/companion_harness/DESIGN.md)（Channels 节）、[docs/imate/USER_MANUAL.md](/docs/imate/USER_MANUAL.md)。
- 代码锚点：[app/external_services/telegram_bot.py](/app/external_services/telegram_bot.py)、[app/services/agent_service.py](/app/services/agent_service.py)、[app/services/agentic_channel/provision.py](/app/services/agentic_channel/provision.py)、[backend/ops/telegram_channel/binding.py](/backend/ops/telegram_channel/binding.py)。
- 外部：[Telegram Business 公告](https://telegram.org/blog/telegram-business)、[Bot Features / Deep Linking](https://core.telegram.org/bots/features)、[Deep links 规范](https://core.telegram.org/api/links)、[Connected business bots](https://core.telegram.org/api/bots/connected-business-bots)。
