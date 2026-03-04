# TTS System 2026-04 行动计划

## 1. 背景与问题定义

近期语音链路出现了两类同源问题：

1. **跨 Provider 模型串线**
   - Gemini 语音路径误用 ElevenLabs 模型 ID（如 `eleven_flash_v2_5`），导致 Vertex 返回 `Invalid Endpoint name`。
   - ElevenLabs 回退路径误用 Gemini 模型 ID（如 `gemini-2.5-pro-tts`），导致 ElevenLabs 返回 invalid uid。
2. **Provider 决策与模型决策分离**
   - Provider 由 `voice_id` 推断，模型却可能来自不匹配的配置来源，缺乏一致性约束。
3. **Fallback 没有重新绑定模型**
   - 跨 Provider 回退时复用原 `model`，进一步放大故障。

根因是当前 TTS 缺少 provider-aware 的模型目录、调用计划对象与启动期校验机制。

## 2. 目标（未来约 3 个月）

### 2.1 业务目标

- 语音生成链路对“模型新增/替换/回退策略调整”具备低风险迭代能力。
- 生产环境中“配置错误导致跨 provider 调错模型”的故障归零。
- 当上游模型行为波动（如 Gemini 返回空音频）时，可稳定按策略降级并可观测。

### 2.2 技术目标

- 建立 **TTS provider-aware 架构**：
  - 模型目录化（catalog）
  - 统一解析与校验（resolver + validator）
  - 显式调用计划（invocation plan）
  - 跨 provider 回退时强制重新选择模型与音色
- 与现有 chat image 成熟模式对齐：allowlist、model family 路由、失败可追踪。

### 2.3 非目标（本阶段不做）

- 不改动 Android API 契约字段（除非后续需求明确）
- 不引入新的 TTS provider（先把 Gemini/ElevenLabs 路由稳定）
- 不做大规模历史数据迁移（仅兼容现有 `voice_id` 前缀与无前缀）

## 3. 设计原则

1. **Fail Loud**：配置与模型不匹配必须尽早失败（启动期/请求早期），不做静默纠错。
2. **Provider 显式化**：任意一次调用都必须明确 provider 与对应 model/voice 的归属。
3. **可组合函数**：拆分为 resolver/planner/executor，避免深层嵌套。
4. **单一职责**：模型选择、回退策略、provider 适配、观测日志分层实现。
5. **与现有模式对齐**：优先复用 `models_catalog + model_selection + family route` 思路。

## 4. 目标架构（TTS V2）

### 4.1 新增 `tts_catalog`（模型目录）

定义 `TTSModelSpec`（建议字段）：

- `provider`: `gemini | elevenlabs`
- `id_on_provider`: 模型真实 ID
- `nickname`: 可读别名（用于配置和运营沟通）
- `supports_language_code`: bool
- `supports_prompted_roleplay`: bool
- `status`: `active | deprecated`

并提供：

- `resolve_tts_model_by_id()`
- `resolve_tts_model_by_nickname()`
- `must_resolve_tts_model_*()`（失败直接抛错）
- `is_model_belongs_to_provider(model, provider)`

### 4.2 新增 `TTSInvocationPlan`

用于在执行前冻结调用计划：

- `provider_selected`
- `model_selected`
- `voice_selected`
- `strategy_selected`（normal / prompted / fallback）
- `fallback_chain`（按 provider 分段）
- `selection_reason`（explicit / config / subscription）

### 4.3 新增 `TTSPlanner`

统一收敛以下决策：

1. 根据 `voice_id` 解析目标 provider
2. 根据 provider 选择默认模型来源
3. 校验显式传入模型是否与 provider 匹配
4. 生成回退链路（同 provider 优先，跨 provider 需重绑定）

### 4.4 调用执行器（Executor）改造

- `GeminiExecutor`：仅接收 Gemini model spec
- `ElevenLabsExecutor`：仅接收 ElevenLabs model spec
- 跨 provider fallback 必须重新构建 `TTSRequest`（模型、音色、输出参数全部重绑定）

## 5. 迭代计划（12 周）

## 阶段 A（第 1-2 周）：止血与护栏

### 交付物

1. 修复跨 provider `model` 串线：
   - Gemini 路径绝不使用 ElevenLabs 模型
   - ElevenLabs 回退路径绝不复用 Gemini 模型
2. 请求级一致性校验：
   - `voice_id` 推断 provider 后，对 `model` 做 provider 归属校验
3. 新增关键测试（见第 7 节）

### 退出条件

- 本地/CI 中新增的 TTS 路由测试全部通过
- 生产无新增 “Invalid Endpoint name” / “invalid uid caused by provider mismatch”

---

## 阶段 B（第 3-6 周）：目录化与调用计划

### 交付物

1. 引入 `tts_catalog` 与 resolver
2. 引入 `TTSInvocationPlan` 与 `TTSPlanner`
3. `VoiceService` 从“边判断边执行”改为“先计划后执行”
4. 启动期配置校验：
   - chat TTS 模型配置必须落在 Gemini allowlist
   - elevenlabs 默认模型必须落在 ElevenLabs allowlist

### 退出条件

- 不合法配置在启动时直接失败
- 运行时不再出现 provider/model 不一致请求

---

## 阶段 C（第 7-12 周）：可运营化与观测

### 交付物

1. fallback 策略配置化（按错误类型分流）
2. 统一观测字段（见第 6 节）
3. Dashboard/告警规则：
   - `gemini_empty_audio_rate`
   - `tts_provider_fallback_rate`
   - `provider_model_mismatch_count`

### 退出条件

- 出现问题时可在 5 分钟内定位：是上游质量问题还是路由/配置问题
- 回退成功率可量化并可对比迭代前后效果

## 6. 观测与日志标准

每次 TTS 调用统一产出结构化字段（建议）：

- `tts_attempt_id`
- `voice_id_raw`
- `provider_selected`
- `model_selected`
- `model_source`（explicit/config/subscription）
- `provider_attempts`（数组，记录每次尝试）
- `fallback_trigger_reason`
- `final_provider`
- `final_model`
- `final_status`（success/failed/empty_audio）

并在 LangSmith trace metadata 中同步关键字段，便于跨链路排障。

## 7. 测试计划（按阶段）

## A 阶段必须新增测试

1. `voice_id=google/...` 且 `model=None`（无 `user/db`）时，最终模型必须为 Gemini 模型。
2. Gemini 失败回退 ElevenLabs 时，fallback request 的 `model_id` 必须为 ElevenLabs 模型。
3. 显式传入 provider 不匹配模型时立即报错（Fail Loud）。
4. 保持现有行为兼容：
   - 语音列表与 `voice_id` 前缀行为不变
   - 返回结构（`VoiceGenerationResult`）不变

## B/C 阶段补充测试

1. `tts_catalog` resolver allowlist 测试
2. `TTSPlanner` 计划生成快照测试
3. fallback 策略矩阵测试（错误类型 -> 下一跳 provider/model）

## 8. 风险与缓解

1. **风险：历史配置值不规范**
   - 缓解：启动期给出清晰错误信息与允许值列表。
2. **风险：Gemini 间歇性空音频继续存在**
   - 缓解：优先同 provider 次级模型重试，再跨 provider 降级；并记录细粒度错误类型。
3. **风险：改造影响现有接口稳定性**
   - 缓解：保持 API 入参与返回结构不变，先做内部 planner/executor 重构。

## 9. 执行顺序建议（可直接开工）

1. 先做 A 阶段（止血 + 测试）并上线。
2. A 阶段稳定后，在同分支推进 B 阶段目录化重构。
3. C 阶段以观测与策略配置化为主，避免一次性大改上线风险。

---

本行动计划覆盖当前故障模式，并对齐仓库内已成熟的多 provider 模型路由实践，目标是在未来 3 个月内建立稳定可扩展的 TTS 演进底座。
