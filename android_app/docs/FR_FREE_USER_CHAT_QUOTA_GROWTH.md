<!-- CREATED_BY_AGENT -->
# FR：Free 用户通过 Daily Check-in + Invite 获取额外聊天额度（Android 方案）

## 1. 需求背景

当前免费用户在触达聊天上限后，会直接进入订阅引导，短期转化有帮助，但也会带来两类问题：

1. 轻度用户在“愿意继续聊”但“暂不付费”时缺少可操作路径。
2. 产品缺少以“聊天额度”驱动的可持续增长闭环（签到留存、邀请裂变）。

本方案目标是在 **不改变 Premium 核心价值** 的前提下，为 Free 用户增加两条可控的额度获取路径：

- Daily Check-in（每日签到）
- Invite Friends（邀请新用户）

---

## 2. 目标与非目标

### 2.1 目标

- 为 Free 用户提供“可解释、可预期、可追踪”的额外聊天额度获取机制。
- 让“聊天额度不足”的场景从单一订阅弹窗，升级为“订阅 + 行为激励”混合转化漏斗。
- 保持与现有 Android 架构兼容：`BoostManager`、`CheckInScreen`、`ChatLimitDialog`、Firebase 埋点。

### 2.2 非目标

- 不在本期重构现有 Credits（Boost）体系。
- 不在本期支持复杂多级分销（仅一跳邀请关系）。
- 不在本期开放 Web 端完整邀请运营后台（先满足 App 使用闭环）。

---

## 3. 核心设计原则

1. **与 Credits 解耦**：聊天额度与 Boost Credits 是两种资源，避免用户认知混淆。
2. **后端为真相源**：额度消耗与奖励发放以服务端为准，客户端只做展示与缓存。
3. **先轻量后增强**：先上线签到增额，再逐步打开邀请奖励和防作弊策略。
4. **失败显式可见**：若奖励不可领/被风控，必须有明确状态，不做静默失败。

---

## 4. 产品方案（用户视角）

## 4.1 额度模型（新增）

- 现有：`base_daily_chat_limit`（后端已存在）
- 新增：`bonus_chat_quota`（可累积、可消耗、可过期）

建议消耗顺序：

1. 先消耗 `base_daily_chat_limit`
2. base 用尽后自动消耗 `bonus_chat_quota`
3. 两者都为 0 时再触发订阅限制弹窗

> 用户文案建议：将 `bonus_chat_quota` 对外展示为 **Bonus Chats**（避免与 Credits 冲突）。

## 4.2 Daily Check-in 奖励

- 适用人群：Free 用户（含 guest/free，策略由后端控制）
- 基础规则：每天可领取 1 次
- 奖励内容：
  - 保留现有 `+200 Credits`
  - 新增 `+N Bonus Chats`（建议默认 N=10，走 Remote Config）
- 连续签到奖励（可配置）：
  - Day 3 额外 +5 Bonus Chats
  - Day 7 额外 +15 Bonus Chats

签到页 `CheckInScreen` 需要新增状态展示：

- 今日可领取 Bonus Chats 数量
- 当前 Bonus Chats 余额
- 连续签到天数与下个里程碑奖励

## 4.3 Invite Friends 奖励

- 每个用户有唯一邀请码（或深链）
- 邀请链路：
  1. 邀请人分享链接
  2. 被邀请人安装并注册/登录
  3. 被邀请人完成激活动作（建议：完成首聊 >= 1 条用户消息）
  4. 发放奖励

奖励建议（可配置）：

- 被邀请人：激活后 +20 Bonus Chats（欢迎奖励）
- 邀请人：每成功邀请 1 人 +40 Bonus Chats

上限建议（可配置）：

- 邀请人每日最多奖励 3 次
- 邀请人每月最多奖励 30 次
- Bonus Chats 钱包上限（例如 500），超出部分不再累计

---

## 5. Android 交互与页面改造

## 5.1 Me 页（`ProfilePage.kt`）

新增入口：

- 保留现有 Daily Rewards Banner
- 新增 Invite Banner（与现有横幅视觉统一）
  - 标题：`Invite Friends`
  - 副标题：`Earn bonus chats when friends join`
  - 点击进入 Invite 页面

## 5.2 Check-in 页（`CheckInView.kt`）

在现有「Claim daily Credits」按钮附近增加：

- `+N Bonus Chats` 文案
- 当前 Bonus Chats 余额
- 连续签到奖励进度

交互要求：

- 若后端返回“已领取”，页面需同步灰态并显示下一次领取时间（或明日可领）。

## 5.3 Chat 限额弹窗（`ChatPage.kt`）

`FREE_USER_SUBSCRIPTION_REQUIRED` 场景下，从单 CTA 升级为三 CTA：

1. `Go Premium`（主 CTA）
2. `Daily Check-in`（次 CTA，若今日未签）
3. `Invite Friends`（次 CTA）

若今日已签，第二 CTA 改为：

- `Come back tomorrow for check-in`

---

## 6. 客户端技术设计（Android）

## 6.1 新增模块建议

建议新增 `app/src/main/kotlin/com/ai/intellimate/quota/`：

- `FreeQuotaModels.kt`
- `FreeQuotaRepository.kt`
- `FreeQuotaViewModel.kt`
- `InviteShareHelper.kt`

## 6.2 与现有模块集成

- `BoostManager`：继续管理 Credits，不承担 Bonus Chats 真相状态。
- `CheckInScreen`：签到成功后刷新 `BoostState + FreeQuotaSummary`。
- `ChatViewModel`：在限额错误时读取 `quota summary` 以决定弹窗 CTA 状态。
- 本地缓存：使用 DataStore 缓存最近一次 quota summary（离线兜底展示，不参与真实扣减）。

## 6.3 Firebase 事件（新增）

建议事件名（100% 采样）：

- `free_quota_checkin_claim_click`
- `free_quota_checkin_claim_success`
- `free_quota_checkin_claim_failed`
- `invite_link_share_click`
- `invite_link_share_success`
- `invite_reward_granted`
- `chat_limit_dialog_cta_click`

关键参数建议：

- `user_type`, `quota_bonus_balance`, `daily_limit`, `used_count`
- `cta_type`（premium/checkin/invite）
- `invite_status`（pending/success/rejected）

---

## 7. 服务端契约建议（为 Android 提供稳定数据）

> 本节是 Android 方案依赖的后端契约，便于联调；实现不在本文范围。

## 7.1 新增/扩展接口

1. `GET /api/v1/free-quota/summary`
2. `POST /api/v1/free-quota/check-in/claim`
3. `POST /api/v1/free-quota/invite/create`
4. `POST /api/v1/free-quota/invite/redeem`

## 7.2 限额错误返回扩展

在现有 `SUBSCRIPTION_REQUIRED` 错误 data 中增加：

- `bonus_chat_remaining`
- `can_check_in_now`
- `next_check_in_at`
- `invite_available`

Android 可据此决定弹窗按钮状态，减少额外请求。

## 7.3 Python-Kotlin 类型同步

按仓库约定，接口字段变化需同步修改：

- Python：`app/schemas`
- Kotlin：`android_app/core/data/src/main/kotlin/ai/sxwl/android/data/api/model`

---

## 8. 反作弊与风控（邀请奖励重点）

最低要求（MVP）：

- 同设备重复注册不发邀请奖励
- 邀请人与被邀请人同账号体系/同设备指纹拦截
- 被邀请人必须完成激活动作才发奖

增强建议（Phase 2）：

- 风险评分（设备、IP、行为速度）
- 奖励延迟到账（pending -> settled）
- 黑名单与人工复核入口

---

## 9. 灰度与配置化

通过 Remote Config 提供开关与参数：

- `enable_free_quota_checkin_bonus`
- `enable_free_quota_invite_bonus`
- `checkin_bonus_chats`
- `invite_bonus_chats_inviter`
- `invite_bonus_chats_invitee`
- `invite_reward_daily_cap`

发布节奏建议：

1. 10% 灰度：仅签到 Bonus Chats
2. 30% 灰度：开放邀请入口
3. 100% 全量：开启完整奖励 + 风控

---

## 10. 验收标准（Definition of Done）

1. Free 用户可通过签到领取 Bonus Chats，并在聊天中自动消耗。
2. Free 用户触达限额时，可从弹窗进入签到/邀请路径继续获取额度。
3. 邀请奖励仅在被邀请用户满足激活条件后发放。
4. 埋点可区分三类路径转化：订阅、签到、邀请。
5. 不影响既有 VIP 与 Credits 逻辑。

---

## 11. 建议实现顺序

1. Android UI 改造：限额弹窗 + Invite 入口（先占位）
2. 后端 summary/claim 接口联调（先签到，再邀请）
3. 埋点与灰度配置上线
4. 风控规则补强与参数调优

