# User time context: server-side timezone inference fallback

**当 client 未上报 timezone 时，从 chat history / 用户画像推断用户 time zone，回填 `## user-time-context` slice，提升对用户 local time 与 Circadian Rhythm 的感知。**

## 背景（现状）

- `## user-time-context` system slice 已存在：[`turn_pipeline.py`](/app/core/companion_harness/companion/turn_pipeline.py) L303-307 注入，渲染逻辑见 [`user_time_context_llm_meta.py`](/app/core/user_time_context_llm_meta.py)。
- 数据 **仅来自 client 上报** 的 `UserTimeContext`（`implicit_signal_bundle.client_time`，见 [`implicit_signals.py`](/app/schemas/implicit_signals.py)、[`chat.py`](/app/schemas/chat.py) `UserTimeContext`）。
- 受 `experimental_enable_chat_with_user_time_context` 门控（默认 `True`，[`config.py`](/app/utils/config.py)）。
- **缺口**：当 client 不上报 timezone（如 WeChat demo bridge、部分 inner-tick 场景）时无 time zone；且没有任何「从 chat history 中位置信息推断时区」的逻辑。

## 待澄清的方向决策（认领前必读）

- **location source（最大 scope 驱动项）**：三选一或组合
  - `USER.md` 身份信息（由 `user_profile_record` 工具写入，最轻量、结构化）
  - raw transcript 扫描（关键词/地名，无额外 LLM 成本，准确率低）
  - 独立 LLM inference step（最准，最贵，需控制触发频率）
- **触发条件**：仅当 `client_time.timezone` 缺失时作为 fallback，避免覆盖 client 真实上报。
- **slice 位置**：维持现有 post-transcript 位置（已满足感知目标），还是移入 `_contextual_system_messages()` leading block —— 需确认。

## TODOs

- [ ] 确认 location source 与触发策略（与人类队友对齐上面三项）。
- [ ] 实现 timezone 推断：在 `client_time.timezone` 缺失时，从选定 source 解析出 IANA tz；解析失败则保持现状（不注入伪造 tz）。
- [ ] 用推断 tz 计算 user local time，回填 `build_companion_user_time_context_system_content` 的输入；保留 client 上报优先级。
- [ ] 为推断结果加可追溯日志（来源 = client / inferred-from-USER.md / inferred-from-transcript）。
- [ ] 端到端验证：client 无 tz 时 slice 仍输出合理 `Time zone:` / `User's time:`；client 有 tz 时行为不变。
