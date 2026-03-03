# TEST_STEPS_DAILY_MEMORY_BONDING

CREATED_BY_AGENT

## 1. 目的

验证 Daily Bonding Note（DBN）从“生成 -> 投递 -> 展示 -> 安全控制”全链路可用，且满足幂等与灰度要求。

## 2. 前置条件

1. PostgreSQL 与 backend 已启动。
2. 已开启以下 flags（按需要）：
   - `enable_daily_bonding_memory_write`
   - `enable_daily_bonding_memory_read`
   - `enable_daily_bonding_prompt_delivery`
3. 测试账号具备可聊天角色与 Love Journal 入口。

## 3. 后端自动化测试步骤

1. 执行与 DBN 相关的单元/集成测试（仅跑新增测试集）。
2. 覆盖以下断言：
   - 同日重复生成不会产生第二条 `daily_bonding`；
   - 重复调用投递接口不会产生第二条 `daily_memory_prompt`；
   - `appVersionCode` 低于阈值时不投递、不返回该类型消息；
   - 关闭用户开关后不投递；
   - 高风险档位命中降级模板。

## 4. 手动联调步骤（API）

1. 准备某 `(user, agent)` 一天内 >= 阈值的聊天数据。
2. 触发 scheduler 或手动执行 DBN 抽取任务。
3. 查询 `memory` 表，确认出现 `memory_type=daily_bonding` 且 `delivery_at IS NULL`。
4. 调用 `GET /api/v1/chats/agents/{agent_id}/messages`：
   - 首次请求应出现 `type=daily_memory_prompt`；
   - 对应 `memory.delivery_at` 被更新；
   - 二次请求不再新增同一 prompt（幂等）。
5. 调用 `GET /api/v1/ai/agents/{agent_id}`：
   - `features.daily_memories` 返回最新条目并可定位。

## 5. 手动联调步骤（Android）

1. 打开与目标角色聊天页，确认出现 DBN 提醒消息。
2. 点击提醒，确认跳转 Love Journal 且定位到对应条目。
3. 验证条目文案结构为 `Moment / Meaning / Next Step`。
4. 在设置关闭 “Daily Bonding Notes” 后重复触发，确认不再收到新提醒。
5. 将客户端版本降到阈值以下，确认提醒类型被过滤。

## 6. 安全回归

1. 构造高风险样本对话，触发 DBN 生成。
2. 验证文案采用降级模板（中性支持，不做亲密升级）。
3. 在 7 天内连续触发 >3 次场景，验证频次上限生效（跳过或延迟投递）。

## 7. 验收结论模板

- 用例通过数 / 失败数
- 失败项与根因
- 是否满足上线门槛（是/否）
- 若否，阻塞项与预计修复时间

## 8. 最近执行进度记录（2026-03-03）

### 8.1 本轮已验证

1. Android 受影响测试任务通过（用于验证本分支合并冲突修复后可继续集成）：
   - `./gradlew :app:testDebugUnitTest :core:common:testDebugUnitTest :core:data:testDebugUnitTest`
2. Kotlin 编译任务通过（用于验证此前 CI 报错点）：
   - `./gradlew :app:compileDebugKotlin`

### 8.2 DBN 后端链路状态

- `test_daily_memory_chat_history_e2e.py` 已在本特性实现阶段加入并通过，覆盖：
  - messages API 投递
  - chat completions 追加 daily prompt choice
  - agent detail 返回 daily memories
  - appVersionCode 门槛生效

### 8.3 当前结论

- **已完成**：DBN 读/投递/展示链路 + Android DTO 同步 + 冲突修复后 Android 编译/单测可通过。
- **待补齐**：DBN 自动生成写入链路（scheduler + LLM）与安全策略完整实现。

