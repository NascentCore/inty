# Daily Bonding Note 实施方案（Love Journal 日常记忆扩展）

CREATED_BY_AGENT

## 1. 目标与成功标准

### 1.1 目标

在现有 Festival Memory 能力基础上，落地一个可灰度发布的 **Daily Bonding Note（DBN）**：

- 每个 `(user_id, agent_id)` 每个本地自然日最多生成 1 条日常记忆；
- 在用户下次进入会话时，以 `daily_memory_prompt` 提醒并跳转 Love Journal；
- 保持安全边界（节奏、强度、依赖风险）可控。

### 1.2 成功标准（上线门槛）

1. 生成正确：同一用户同一角色同一本地日期不会重复写入。
2. 投递正确：同一条 DBN 提醒仅投递一次（幂等）。
3. 展示正确：Android Love Journal 可展示并定位 DBN 条目。
4. 安全正确：高风险用户自动降强度/降频，不触发亲密升级文案。
5. 业务正确：灰度组 D7 留存与“被理解/被记住”反馈不低于对照组。

## 2. 范围与边界

### 2.1 本期范围（MVP）

- 新增 `memory_type=daily_bonding` 的写入、读取、按需投递闭环。
- 复用节日记忆的投递轨道（chat completions + messages list）。
- Love Journal 增加 daily 条目展示（与 festival 并存）。
- 增加基础安全控制：频次上限 + 风险降级模板 + 用户可关闭开关。

### 2.2 非目标（本期不做）

- 不做全量记忆检索重排重构（`relevance*recency*salience*novelty` 全局化后续做）。
- 不改主对话上下文拼装策略（只处理 prompt 型提醒消息）。
- 不做复杂个性化配置中心（仅提供开关与默认策略）。

## 3. 总体架构与调用链

### 3.1 生成链路（离线/准实时）

1. Scheduler 每小时扫描“前一日已结束窗口”候选 `(user, agent)`。
2. 读取当日消息，执行 eligibility（轮数、情绪显著性、安全门控）。
3. 通过 LLM 生成 3 段式 DBN（Moment / Meaning / Next Step）。
4. 写入 `memory` 表，`delivery_at=NULL`，等待按需投递。

### 3.2 投递链路（在线按需）

1. 用户触发 `POST /api/v1/chat/completions/{agent_id}` 或 `GET .../messages`。
2. 读取 `(user, agent)` 下 `delivery_at IS NULL` 的 DBN（受版本与用户开关约束）。
3. 写 `chat_history` 一条 `messageType=daily_memory_prompt` 提醒消息并回填 `delivery_at`。
4. 客户端点击提醒，深链进入 Love Journal 对应 DBN 条目。

### 3.3 展示链路（客户端）

- `GET /api/v1/ai/agents/{agent_id}` 返回 `features.daily_memories`（或统一时间线条目）。
- Android Love Journal 以“Yesterday/日期 + 三段内容 + 引导语”渲染。

## 4. 数据模型与迁移

### 4.1 `memory` 表扩展

- `memory_type` 新增值：`daily_bonding`。
- `metadata`（JSON）约定字段：
  - `local_date: YYYY-MM-DD`
  - `timezone: IANA string`
  - `emotional_salience: float(0~1)`
  - `source_message_count: int`
  - `risk_tier: low|medium|high`

### 4.2 幂等与唯一性

新增唯一索引（PostgreSQL 表达式索引）：

- 唯一键语义：`(user_id, agent_id, memory_type, metadata->>'local_date')`。
- 目的：数据库层强约束“每日最多一条”，避免并发重复写。

### 4.3 迁移步骤

1. `alembic upgrade head` 确保本地最新。
2. 新增 revision：
   - 扩展 `memory_type` 可选值（若当前用字符串约束/枚举则同步）。
   - 创建唯一表达式索引。
3. 回归检查：老数据（festival/user_common/user_agent）读写不受影响。

## 5. 配置与特性开关

### 5.1 config.yaml（建议新增）

```yaml
daily_bonding_memory:
  enabled: true
  enabled_since: "2026-03-01T00:00:00Z"
  min_rounds_in_day: 8
  scheduler_run_minute_utc: 10
  max_deliveries_per_7d: 3
  min_app_version_code: 0
```

### 5.2 Feature Flags

- `enable_daily_bonding_memory_write`
- `enable_daily_bonding_memory_read`
- `enable_daily_bonding_prompt_delivery`

要求：读写、投递分别可控，便于灰度与快速回滚。

## 6. 后端实施任务分解（按模块）

### 6.1 数据层与 Schema

- `app/models/memory.py`
  - 增加 `daily_bonding` memory_type 支持。
- `app/schemas/agent.py`
  - 增加 `DailyMemoryItem`，并在 `AgentFeatures` 暴露 `daily_memories`。
- 如有 Kotlin API 数据类型镜像，需同步 `android_app/core/data/.../api/model`。

### 6.2 业务服务

- 新增 `app/services/daily_bonding_service.py`
  - `collect_day_messages(user_id, agent_id, local_date, timezone)`
  - `check_daily_bonding_eligibility(...)`
  - `summarize_daily_bonding_note(...)`
  - `extract_daily_bonding_and_save(...)`
- `app/services/memory_service.py`
  - `get_undelivered_daily_memories(...)`
  - `deliver_daily_memories_for_user_agent(...)`
- `app/services/chat_history_service.py`
  - `add_daily_memory_prompt_message_sync(...)`
  - `get_messages_paginated(...)` 中映射 `daily_memory_prompt` 类型。

### 6.3 API 接口接入

- `app/api/v1/endpoints/chat.py`
  - chat completion 后追加 DBN 按需投递逻辑；
  - 当次 `choices` 可返回 `daily_memory_prompt`。
- `app/api/v1/endpoints/chats.py`
  - 拉取消息时触发 DBN 投递；
  - 版本门槛不满足时隐藏该类型消息。
- `app/api/v1/endpoints/agents.py`
  - 角色详情返回 `features.daily_memories`。

### 6.4 调度与任务

- `app/services/push_scheduler_service.py`
  - 新增 `_run_daily_bonding_extraction`，按小时扫描；
  - 使用“先占位再执行”策略避免多实例重复执行（参考节日记忆任务模式）。

### 6.5 安全控制

- 在 `daily_bonding_service` 注入风险门控：
  - `high risk` -> 使用中性支持模板；
  - 超频（7天>3次）-> 跳过生成或延迟投递；
  - 用户关闭开关 -> 不投递。

## 7. Android / Evaluation 实施任务

### 7.1 Android

- 模型层新增 `daily_memory_prompt` 与 `daily_bonding` 条目映射。
- Love Journal 页：
  - 新增 daily 分组/标记；
  - 点击提醒深链到指定条目；
  - 增加“关闭 Daily Bonding Notes”开关入口。

### 7.2 Evaluation

- 管理页新增 DBN 配置可视化（开关、阈值、频次上限）。
- 运营查看维度：生成量、投递量、打开率、纠错率。

## 8. 监控、埋点与报表

### 8.1 事件定义（建议）

- `daily_bonding_generated`
- `daily_bonding_delivered`
- `daily_bonding_opened`
- `daily_bonding_user_corrected`
- `daily_bonding_safety_downgraded`

### 8.2 看板最小集

- 漏斗：生成 -> 投递 -> 打开 -> 回复；
- Cohort：flag on/off 的 D1/D7/D30；
- 安全：高风险降级触发率、夜间过度使用趋势。

## 9. 测试与验收

详细步骤见：`tests/docs/TEST_STEPS_DAILY_MEMORY_BONDING.md`。

本期必须覆盖：

1. DB 写入幂等（并发场景）；
2. 提醒投递幂等（重复请求场景）；
3. 版本门槛过滤；
4. Love Journal 深链定位；
5. 用户关闭开关后的抑制行为；
6. 安全降级模板命中行为。

## 10. 里程碑与排期（建议 3 周）

### Week 1（后端主链路）

- migration + model/schema
- daily_bonding_service + scheduler
- API 接入（写入、读取、投递）
- 后端自动化测试通过

### Week 2（客户端与联调）

- Android Love Journal 展示 + 深链
- 开关接入 + 版本门槛验证
- Evaluation 配置/报表基础页

### Week 3（灰度上线）

- 5% 灰度（订阅用户优先）
- 观察 3~5 天：留存、反馈、安全指标
- 决策扩容到 25% -> 50% -> 100%

## 11. 风险与回滚

### 11.1 主要风险

- 文案重复导致“机械感”
- 并发重复投递
- 误触发高强度依赖语气

### 11.2 回滚策略

1. 立即关闭 `enable_daily_bonding_prompt_delivery`（先止损前台体验）。
2. 必要时关闭 `enable_daily_bonding_memory_write`（停止新数据写入）。
3. 保留已写入数据，不做硬删除；后续脚本修复后再恢复投递。

## 12. 交付物清单

1. Alembic migration（含唯一索引）。
2. 后端服务与 API 改造 PR。
3. Android 展示与深链 PR。
4. Evaluation 配置与报表 PR。
5. 测试证据（自动化结果 + 手动验收记录 + 灰度日报模板）。

