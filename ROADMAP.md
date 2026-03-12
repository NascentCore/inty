# IntelliMate Android App Roadmap

## 执行状态总览（2026-03-12，基于代码库扫描）

> 判定口径：  
> - 已完成：主链路代码 + 接口/任务 + 测试证据已具备  
> - 进行中：已有可用实现，但仍有缺口/未形成完整闭环  
> - 未开始：暂未发现可确认实现

### 总体判断

- Phase 1：**进行中（约 70%）**，记忆 MVP 已落地，其余条目多为“已上线基础能力 + 持续优化”。
- Phase 2：**进行中（约 60%）**，语音、推荐、会员边界已有较强实现，消息管理与关系增强仍在补齐。
- Phase 3：**进行中（约 35%）**，Ops 产品化已形成，A/B 与 D90 指标标准化链路仍待完善。

### 分项执行情况

#### Phase 1（0-2 个月）：打牢长期陪伴基本盘

- 对话稳定性：**进行中**
  - 已有多层 Prompt 组装、历史窗口控制、日期上下文注入与相关测试。
  - 证据：`app/core/agent/agent.py`、`tests/app/core/agent/test_agent_history_window_limits.py`、`tests/app/core/agent/test_agent_date_context.py`
- 记忆 MVP：**已完成（MVP）**
  - 已落地 `festival`/`daily_bonding` 记忆、按需投递、`delivery_at` 幂等与 E2E 测试。
  - 证据：`app/models/memory.py`、`app/services/memory_service.py`、`app/api/v1/endpoints/chat.py`、`app/api/v1/endpoints/chats.py`、`tests/app/features/test_daily_memory_chat_history_e2e.py`、`tests/app/features/test_festival_memory_chat_history_e2e.py`
- 消息回访机制（Push + 回流）：**进行中**
  - 已有多阶段 push、已读回写、节日记忆推送批处理；会话“红点”跨端一致性仍需继续明确。
  - 证据：`app/services/push_notification_service.py`、`app/services/push_scheduler_service.py`、`app/models/push_notification.py`
- 信任能力（隐私/举报/删号）：**进行中**
  - 举报与删号链路已可用；隐私“说明/治理”体验仍有优化空间。
  - 证据：`app/api/v1/endpoints/report.py`、`app/api/v1/endpoints/users.py`、`app/services/user_service.py`、`tests/app/api/v1/endpoints/test_user_deletion.py`
- 订阅基础优化：**进行中**
  - 购买校验、恢复/续订状态处理、RTDN webhook 已有实现；到期提醒闭环仍需继续完善。
  - 证据：`app/api/v1/endpoints/subscription.py`、`app/services/subscription_service.py`、`tests/app/services/test_subscription_service.py`

#### Phase 2（2-4 个月）：从“能聊”升级到“有陪伴感”

- 语音优先体验：**进行中（主链路已上线）**
  - 语音通话页面、WS 实时链路、TTS 音色与生成流程已具备；“进一步优化”仍持续推进。
  - 证据：`android_app/app/src/main/kotlin/com/ai/intellimate/call/VoiceCallScreen.kt`、`android_app/app/src/main/kotlin/com/ai/intellimate/call/VoiceCallViewModel.kt`、`app/api/v1/endpoints/live_chat.py`、`app/api/v1/endpoints/text_to_speech.py`
- 关系感增强（记忆卡片/关键时刻）：**进行中**
  - 节日记忆链路较完整，daily bonding 仍有待补齐写入自动化与观测埋点。
  - 证据：`docs/FR_FESTIVAL_MEMORY.md`、`docs/FR_DAILY_MEMORY_BONDING_IMPLEMENTATION.md`
- 推荐与探索升级：**已完成（核心能力）**
  - Explore 分页、刷新、缓存与后端推荐排序策略已落地。
  - 证据：`android_app/app/src/main/kotlin/com/ai/intellimate/explore/ExploreViewModel.kt`、`android_app/app/src/main/kotlin/com/ai/intellimate/explore/ExplorePagingSource.kt`、`app/services/agent_service.py`、`app/api/v1/endpoints/agents.py`
- 消息管理增强（分层/收藏/回访）：**进行中**
  - 端侧已支持 Pin/Hide/Favorite；后端跨端同步能力尚未形成统一方案。
  - 证据：`android_app/app/src/main/kotlin/com/ai/intellimate/messages/MessagesViewModel.kt`、`android_app/core/data/src/main/kotlin/ai/sxwl/android/data/store/IntySetting.kt`
- 会员价值明确化：**已完成（基础分层）**
  - Android 与后端均已形成免费/付费能力边界与限额门控。
  - 证据：`android_app/core/data/src/main/kotlin/ai/sxwl/android/data/billing/VipStatusHelper.kt`、`android_app/app/src/main/kotlin/com/ai/intellimate/chat/ui/ChatSettingsDrawer.kt`、`app/services/subscription_service.py`

#### Phase 3（4-6 个月）：构建可持续增长与口碑

- 陪伴闭环产品化（记忆+语音+push+推荐）：**进行中**
  - 各模块均有实现并已发生联动，但“统一闭环指标看板”仍需收敛。
  - 证据：`app/services/memory_service.py`、`app/services/voice_service.py`、`app/services/push_notification_service.py`、`app/services/agent_service.py`
- 角色生态扩展（创建/审核）：**进行中**
  - evaluation/ops 具备评测与批量流程，但部分高级能力仍为占位接口。
  - 证据：`backend/ops/api/v1/evaluation.py`、`app/services/evaluation_service.py`
- 轻运营能力产品化：**已完成（核心形态）**
  - Ops 已独立部署形态，且包含节日记忆与报表能力。
  - 证据：`backend/ops/main.py`、`backend/ops/api/v1/router.py`、`backend/ops/api/v1/festival_memory.py`
- 数据驱动迭代（A/B）：**进行中**
  - 已有实验 SQL 与部分功能灰度设计；尚未形成统一、标准化的生产实验框架。
  - 证据：`scripts/sql/ab_test_minimax_vs_gemini_20260207.sql`、`docs/FR_DAILY_MEMORY_BONDING.md`

### 指标验收状态（当前）

- D7/D30 相关能力：**可观测基础已具备，结果需按版本窗口持续复盘**（报表与分析入口已存在）。
- D90 与口碑类指标：**进行中**，目前更偏“可查询能力已具备”，标准化 KPI 看板仍需补齐。
- 证据：`app/services/user_analytics_report_service.py`、`backend/ops/api/v1/evaluation.py`、`evaluation/pages/UserAnalyticsPage.tsx`

## 目标用户与产品北极星

- 目标用户：35+ 美国男性，寻求长期、稳定、低负担的 AI 情感陪伴。
  - 2026 Q2 扩展到 18-25 岁女性用户
- 北极星目标：让用户在 90 天内持续形成“固定角色 + 固定互动习惯”。
- 产品定位：以聊天为核心，语音与轻量内容为增强，订阅为商业化承载。

## 优先级原则（用于所有需求取舍）

- 先做“关系连续性”，再做“功能新鲜感”。
- 先做“稳定和信任”（可靠性、隐私、可控性），再做“花哨扩展”。
- 任何新增功能都要服务于至少一个核心指标：留存、互动深度、付费转化。

## 关键能力优先级（1-10 分）

- 对话质量与人格稳定性：**10/10**
- 长期记忆与关系连续性：**10/10**
- 语音体验（语音通话 + TTS）：**9/10**
- 消息回访机制（Push + 会话管理）：**9/10**
- 隐私与账户控制（删号、举报、边界）：**9/10**
- 订阅与支付体验：**8/10**
- 角色发现与推荐效率：**8/10**
- 消息中心高级管理（置顶、隐藏、收藏）：**7/10**
- 角色创建与编辑：**7/10**
- 图片生成与视觉玩法：**6/10**
- 积分/Boost/签到：**6/10**
- 聊天背景等装饰能力：**5/10**

## 分阶段路线图

### Phase 1（0-2 个月）：打牢长期陪伴基本盘

- 提升对话稳定性：减少“人设漂移”、减少答非所问、强化上下文一致性。
- 上线记忆 MVP：长期偏好、关键事件、关系里程碑可被稳定召回。
- 强化消息回访：推送触达优化、会话红点与回流链路打通。
- 完善信任能力：隐私说明、举报反馈、账号删除体验更清晰。
- 订阅基础优化：购买失败提示、恢复购买、到期提醒流程简化。

**阶段验收指标**
- D7 留存提升
- 人均会话时长提升
- 对话中断率下降
- 订阅支付成功率提升

### Phase 2（2-4 个月）：从“能聊”升级到“有陪伴感”

- 语音优先体验：语音通话稳定性、响应延迟、打断控制进一步优化。
- 关系感增强：记忆卡片/关键时刻回顾（如节日、周年）自然嵌入聊天。
- 推荐与探索升级：更快匹配合适角色，减少用户“找不到想聊的人”。
- 消息管理增强：会话分层、收藏角色管理、回访路径更短。
- 会员价值明确化：围绕高频能力设计清晰的免费/付费边界。

**阶段验收指标**
- D30 留存提升
- 每周互动天数提升
- 语音使用占比提升
- 订阅续费率提升

### Phase 3（4-6 个月）：构建可持续增长与口碑

- 陪伴闭环产品化：记忆、语音、推送、个性化推荐形成稳定循环。
- 角色生态扩展：优化创建流程与审核体验，提升优质角色供给。
- 轻运营能力产品化：活动触达不过度打扰，确保“有价值才触达”。
- 数据驱动迭代：围绕留存与付费转化持续做 A/B 实验。

**阶段验收指标**
- D90 留存提升
- 核心用户月互动时长提升
- 口碑相关指标（评分/好评率）提升

## 明确不优先（当前阶段）

- 复杂重社交系统（高运营成本、偏离“私密陪伴”核心）。
- 过度游戏化机制（会削弱成熟用户对产品“真实陪伴感”的预期）。
- 大量视觉皮肤型需求（投入高、对长期留存贡献有限）。

## 备注

- 本路线图优先服务 Android 侧现有能力迭代，不引入过多新复杂系统。
- 每个阶段结束都需要基于真实数据复盘，再决定下一阶段资源分配。
