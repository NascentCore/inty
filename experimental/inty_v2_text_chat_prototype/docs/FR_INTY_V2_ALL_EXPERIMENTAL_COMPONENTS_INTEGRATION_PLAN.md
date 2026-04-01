# FR_INTY_V2_ALL_EXPERIMENTAL_COMPONENTS_INTEGRATION_PLAN

## 1. 目标

- 将 `experimental/` 下与 agentic companion AI 相关的实验能力，按统一控制面逐步整合到 `experimental/inty_v2_text_chat_prototype`。
- 保持 `orchestrator.run_turn` 作为单一编排入口，避免多套会话写入路径。
- 先统一契约与可观测性，再并入高价值能力，最后处理外围能力与灰度策略。

## 2. 范围定义

### 2.1 P0-直接并入（核心能力）

- `experimental/agentic_ai_companion`
  - heartbeat 主动回合
  - `generate_image` / `text_to_speech` / `live_voice_message_reply`
  - memory compaction（长对话上下文压缩）
- `experimental/perpetual_agent`（含 `core_v2`）
  - 单消费者租约
  - scheduler / admin replay 运行时
  - Telegram 入站循环与出站回复
- `experimental/agentic_loop_sleep_demo`
  - agentic loop 最小语义与工具循环约束

### 2.2 P1-高价值支撑能力

- `experimental/memory_prompt_benchmark`
  - tool trigger 与 memory 注入结构评测
- `experimental/prompt_layer`
  - prompt 版本管理与可追踪
- `experimental/voice_chat`
  - Android WebRTC -> FastAPI -> Gemini Live 桥接能力
- `experimental/gemini_native_audio_websocket_demo` + `experimental/s2s`
  - 语音实时链路稳定性与重连策略验证

### 2.3 P2-外围能力（延后，按需接入）

- 运营与分析：`user_analytics`、`firebase_remote_config`、`firebase_events*`、`fcm_token_getter`
- 增长与广告：`google_web_ads`
- 评测与性能：`locust_test`、`fastapi_otel`
- 内容与素材：`image_model_benchmark`、`fal_ai`、`comfyui`、`civitai`、`aigc`、`generate_opening_audio`

## 3. 统一目标架构（落到 inty_v2_text_chat_prototype）

- `main.py` / CLI：统一入口（`repl`/`once`/`bootstrap-agent`/`serve-*`）
- `orchestrator.py`：唯一 turn 编排与持久化入口
- `models.py`：
  - 统一内部事件契约（兼容 text/image/audio/video 的 `content_parts`）
  - 统一会话上下文契约（`context_mode`, `user_id`, `companion_id`, `chat_id`）
- `workspace_init_tools.py` + tool registry：
  - 所有工具声明、参数 schema、执行映射统一管理
- `memory_update.py` + memory store：
  - 日记层、日总结、长期记忆、压缩策略统一
- `core_v2/` 子域（可在 `inty_v2_text_chat_prototype/core_v2` 新建）：
  - lease/retry/scheduler/admin/repository
- `bridges/`（新增建议）：
  - Telegram bridge、voice bridge、websocket bridge 统一挂接

## 4. 分阶段实施计划

### Phase 0 - 契约冻结与基线（先做）

- 冻结契约：
  - turn input/output
  - transcript 行结构（含 `uuid`/`trace_id`）
  - tool call envelope
  - heartbeat synthetic turn 规范
- 建立统一目录约束：
  - 新增 `docs/FR_INTY_V2_INTEGRATION_CONTRACTS.md`
  - 新增 `tests/docs/TEST_STEPS_INTY_V2_INTEGRATION_SMOKE.md`
- 验收：
  - `run_turn` 仍是唯一写 assistant transcript 路径
  - 现有 `repl` 与 `once` 行为无回归

### Phase 1 - 工具与记忆并轨（最高优先）

- 并入 `agentic_ai_companion`：
  - 将生图/TTS/Live voice 工具收敛到统一 registry
  - 将 memory compaction 融入 `memory_update.py` 可选策略
- 并入 `agentic_loop_sleep_demo`：
  - 以测试形式固化工具循环状态机
- 验收：
  - 工具调用链路统一且可观测（`llm_trace.jsonl` + `tool_background.jsonl`）
  - 开启/关闭 compaction 时行为可控且可复现

### Phase 2 - 渠道与自治并轨（高优先）

- 并入 `perpetual_agent/core_v2`：
  - 迁移 lease/scheduler/retry/repository 到 `inty_v2` 子模块
  - Telegram inbound/outbound 接入统一 turn pipeline
- 验收：
  - 单消费者租约成立
  - scheduler 幂等
  - Telegram 消息经统一 `run_turn` 链路落 transcript

### Phase 3 - 语音实时链路并轨（中高优先）

- 并入 `voice_chat`、`gemini_native_audio_websocket_demo`、`s2s` 的可复用部分：
  - 语音桥接接口标准化（输入 PCM/输出 PCM）
  - 重连策略、turn complete 行为一致化
- 验收：
  - 语音回合可写入统一 transcript（文本转写 + 元数据）
  - 长连接断开后能按策略恢复

### Phase 4 - 评测与灰度系统（中优先）

- 并入 `memory_prompt_benchmark` 与 `prompt_layer`
  - 建立 prompt 版本对比、memory 注入策略对比、tool trigger 回归评测
- 并入外围能力（按需）
  - 通过 feature flag 方式接入运营和增长能力，不污染核心编排
- 验收：
  - 每次策略变更都可通过统一 benchmark 产出报告
  - feature flag 可关闭非核心能力

## 5. 组件映射清单（来源 -> 目标）

| 来源目录 | 目标模块 | 处理方式 | 优先级 |
|---|---|---|---|
| `agentic_ai_companion` | `tools/*`, `memory_update.py`, `async_repl` | 直接迁移 + 统一接口 | P0 |
| `perpetual_agent/core_v2` | `core_v2/*` | 子模块迁移 + 适配层 | P0 |
| `perpetual_agent/telegram_*` | `bridges/telegram_*` | 协议复用 + pipeline 对齐 | P0 |
| `agentic_loop_sleep_demo` | `tests/` + `orchestrator` contract | 转为回归测试 | P0 |
| `memory_prompt_benchmark` | `evaluation/memory_trigger/*` | 评测工具化 | P1 |
| `prompt_layer` | `prompting/versioning/*` | 轻量接入 | P1 |
| `voice_chat` | `bridges/voice_webrtc/*` | 接口抽象后并入 | P1 |
| `gemini_native_audio_websocket_demo` | `bridges/voice_ws/*` | 重连策略与会话管理复用 | P1 |
| `s2s` | `bridges/voice_terminal/*` | 保留为调试通道 | P1 |
| 其余外围目录 | `integrations/*` 或保持独立 | 延后 + feature flag | P2 |

## 6. 测试与验收矩阵

### 6.1 每阶段通用验收

- 功能验收：
  - reactive turn 正常
  - heartbeat turn 正常
  - tool turn 正常
- 一致性验收：
  - 所有渠道都走统一 turn pipeline
  - transcript 写入结构一致
- 回归验收：
  - 现有 `inty_v2_text_chat_prototype/tests/` 全通过

### 6.2 阶段专项验收

- Phase 1：
  - chat-to-image、TTS、live voice 可分别触发并返回可用产物路径
  - memory compaction 开关前后差异可测
- Phase 2：
  - `core_v2` 租约/调度相关测试通过
  - Telegram 端到端单消费者行为稳定
- Phase 3：
  - 语音 websocket/webRTC 断线重连可复现
  - 语音 turn 的 transcript 与追踪日志完整
- Phase 4：
  - memory/tool trigger benchmark 可固定参数重复运行并产出报告

## 7. 风险与缓解

- 风险 1：多来源工具定义冲突（同名/参数不一致）
  - 缓解：先统一 tool registry，强制 schema 校验
- 风险 2：多入口写消息导致历史分叉
  - 缓解：强制所有入口调用 `run_turn` 或等价单写入函数
- 风险 3：语音链路引入高延迟影响文本体验
  - 缓解：语音桥接与文本编排隔离，默认关闭语音通道
- 风险 4：外围实验能力侵入核心路径
  - 缓解：feature flag + 分层目录 + P2 延后策略

## 8. 里程碑与退出条件

- M1（Phase 0-1 完成）
  - 工具与记忆并轨完成，核心聊天链路不回归
- M2（Phase 2 完成）
  - 自治与 Telegram 并轨完成，调度稳定
- M3（Phase 3 完成）
  - 语音实时链路并轨完成，可端到端演示
- M4（Phase 4 完成）
  - 评测与灰度体系上线，支持持续策略优化

退出条件：

- 达成 M4 后，`experimental/` 中 P0/P1 原型目录进入只读归档状态（仅保留文档与历史测试数据），新的 companion 能力只在 `inty_v2_text_chat_prototype` 迭代。

