<!-- CREATED_BY_AGENT -->
# Boost AI Characters 功能设计与实现计划

## 目标与背景
- 通过「角色打榜」玩法，将每日签到等轻任务与真实聊天行为绑定，提升留存与会话深度。
- 纯前端实现 MVP，不新增或修改后端接口；所有数据均以本地/缓存方式模拟。
- 为后续后端支持预留清晰的数据契约，便于逐步切换到真实排行榜。

## 核心概念
- **Token Energy**：用户每日通过签到、活动奖励等方式领取的额度，直接与聊天 token 消耗挂钩。
- **Points**：基于 Token Energy 或聊天 token 消耗实时折算的积分，兑换比例在客户端常量中配置（默认 1 Point = 1 Token Energy）。积分只在本地存储，刷新即重置。
- **Boost**：一次打榜行为，消耗 100 Points（可配置），为当前 AI 角色累积人气。
- **Top Boosted Characters**：按 Boost 次数排序的排行榜，默认展示前 100 个角色，可作为 Explore 页签的子 Tab。

## 用户旅程
1. **签到/活动**：用户触发签到即获得 Token Energy，提示当前可用积分。
2. **聊天转化**：聊天时根据 token 消耗实时折算并累积 Points。
3. **Explore 子 Tab**：用户进入 Explore → Boost 子 Tab，浏览 Top 100 AI 角色，点击即可跳转聊天。
4. **聊天页面 Boost 图标**：在对话顶部右侧增加 Boost 按钮，展示可用 Points、缺口提示，并允许一次性投入 ≥100 Points 的整数倍。

## UI/UX 要点
- **签到反馈**：Toast + 积分条动画，突出「今日剩余 X Points」。
- **Explore 子 Tab**：
  - 排行列表：角色头像、名称、Boost 计数、涨幅趋势箭头。
  - 按钮：`Boost`（直接打开对应聊天并聚焦 Boost 面板）与 `Chat`。
  - 空状态：若无数据，展示「暂无打榜数据，去聊天赚积分」。
- **聊天顶部栏**：
  - 右侧新增火焰/火箭图标，携带数字徽章（剩余 Points）。
  - 点击后弹出半屏面板：角色简介、当前 Boost 总数、输入消耗 Points 的滑条或步进器（每步 100）。
  - 成功后在对话流插入系统消息提示。

## 客户端数据模型（本地）
```kotlin
data class BoostState(
    val availablePoints: Int,
    val boostsByAgent: Map<String, AgentBoostInfo>,
    val dailyEnergyEarned: Int,
    val lastReset: LocalDate
)
```
- **AgentBoostInfo**：包含 `agentId`, `agentName`, `avatarUrl`, `boostCount`, `lastBoostedAt`。
- 数据持久化于 EncryptedSharedPreferences 或 Proto DataStore，并提供 `resetIfNewDay()`。

## 业务逻辑
- **积分来源**：
  - 签到：固定奖励（如 200 Points）。
  - 聊天：按 token 使用量实时增加，可基于消息估算字数。
  - 其他活动：预留枚举类型，便于未来扩展。
- **Boost 约束**：
  - 每次至少 100 Points，可配置 `BOOST_STEP_POINTS`。
  - 若不足显示入口灰态，点击弹出缺口提示与快速入口（如「去签到」）。
  - 同一角色不限 Boost 次数；排行榜以本地累积排序。
- **排行榜**：
  - 客户端根据 `boostCount` 排序，截取前 100。
  - 若需要「推荐角色」接口的 Top Boost 过滤，可在现有推荐函数添加 `BoostRanking` 选项，优先使用本地数据，未来替换为服务器来源。

## 实现分层
1. **Domain 层**
   - `BoostRepository`: 管理积分余额、Boost 记录、排行榜。
   - `BoostCalculator`: 负责 Token → Points 折算策略。
   - `LeaderboardProvider`: 输出 Explore Tab 所需的分页数据。
2. **ViewModel 层**
   - `BoostViewModel`: 提供签到奖励、排行榜、Boost 动作的状态流。
   - `ChatHeaderViewModel`：订阅 Boost 状态，驱动徽章与弹窗。
   - `ExploreViewModel`：新增 `Boost` Tab 状态，支持切换过滤条件（热门、推荐、Boost）。
3. **UI 层**
   - Compose 组件：`BoostChip`, `BoostSheet`, `BoostLeaderboardTab`, `BoostEmptyState`。
   - 动画与可访问性：按钮禁用、积分变化过渡、TalkBack 描述。

## 与推荐系统的集成计划
- 在现有「推荐角色」请求参数中加入 `variant = BOOSTED_TOP`.
- 未有后端时，`variant = BOOSTED_TOP` 走客户端排行榜。
- 当后端接口上线时，仅需在 Repository 内切换数据源即可。

## 事件与埋点
- `boost_token_earned`：来源（签到/聊天）、数量。
- `boost_invested`：角色 ID、投入 Points、剩余余额。
- `boost_leaderboard_viewed`：序号区间。
- `boost_shortage_prompted`：触发缺口弹窗。
> 无后端时先走本地事件缓冲，后续接入现有 analytics 管线。

## 风险与对策
- **本地排行榜与真实数据不一致**：在文案中标注「本地体验版」，避免与服务器冲突。
- **数据丢失**：使用 DataStore + 定期备份至云端占位（待后端）。
- **Token 估算误差**：允许运维通过远程配置调整折算比例。
- **用户频繁点击 Boost**：100 Points 阈值 + 提示冷却动画。

## 推出策略
1. **Phase 0**：隐藏开关 + 内测，验证 UI/UX。
2. **Phase 1**：灰度 10% 用户，观察 Boost 行为、Crash、性能。
3. **Phase 2**：全量发布，同时准备后端排行榜需求文档。

## 开发任务拆解
- **数据与逻辑**
  1. 新建 `BoostRepository`, `BoostCalculator`, 单元测试覆盖折算与阈值。
  2. 在签到与聊天模块内触发 `addPoints(source, amount)`。
- **UI 入口**
  3. Explore 页面新增 `Boost` 子 Tab 与列表组件。
  4. Chat 顶部栏新增 Boost 图标与弹窗，联合测试积分扣减流程。
- **推荐与配置**
  5. 推荐接口新增 `variant` 参数枚举，默认值保持现有逻辑。
  6. 远程配置支持调节 `BOOST_STEP_POINTS`, `BOOST_DAILY_REWARD`.
- **QA & 验证**
  7. 编写 E2E 测试脚本（签到→积分→Boost→排行榜刷新）。
  8. 可视化埋点验证，确保事件参数完整。

## 后续待办
- 拟定后端接口：`GET /agents/boosted`, `POST /agents/{id}/boost`.
- 设计跨设备同步策略，避免多端积分差异。
- 与产品确认积分兑换是否可逆、是否允许赠送给好友。

