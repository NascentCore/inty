# FR_INTY_V2_PHASED_EXPERIMENTAL_COMPONENTS_INTEGRATION_PLAN

## 1. 目标

- 将 `experimental/` 下与 agentic companion AI 相关的实验能力，按统一控制面分阶段整合到 `experimental/inty_v2_text_chat_prototype`。
- 保持 `orchestrator.run_turn` 作为单一编排入口，避免多套会话写入路径。
- 先统一契约与可观测性，再并入高价值能力，最后处理外围能力与灰度策略。

### 1.1 范围口径（修正 "all" 语义）

- 本文档覆盖 "全部实验组件的盘点与去向"，不是 "一次迭代整合全部组件"。
- 对全部组件必须给出三类结果之一：
  - 已并入核心路径（P0/P1）
  - 延后并入但已绑定强制里程碑（P2 with M5）
  - 明确永久独立并给出边界（需在文档中显式标注）
- 未出现在映射表中的目录，视为计划缺失，不允许进入实现阶段。

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

- `research/memory_prompt_benchmark`（仓库内已从 `experimental/memory_prompt_benchmark` 迁出；不在 `experimental/` 下）
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

### 2.4 `experimental` 自包含规则冲突处理

- 现有 `experimental/README.md` 要求子目录自包含、不依赖外部目录。
- 本计划采用双阶段策略，避免直接违反规则：
  - 阶段 A（过渡期）：各来源目录保留独立可运行入口，仅在 `inty_v2_text_chat_prototype` 增加桥接适配层。
  - 阶段 B（收敛期）：能力迁移完成后，将来源目录标记为 archive，只保留 README、测试证据、迁移指引。
- 进入阶段 B 前必须完成：
  - 新路径功能验收通过
  - 旧路径 README 加 "迁移到 inty_v2" 指针
  - `tests/docs` 中对应测试步骤同步到新路径

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

### 3.1 不可变约束（Phase 0 必须冻结）

- `orchestrator.run_turn` 仍是 assistant transcript 单写入入口。
- `prompts.build_system_prompt` 顺序不变（含 `AGENTS.md`/`TOOLS.md`/`HEARTBEAT.md` 及 `context_mode` 语义）。
- runnable workspace 必选文件不变：`IDENTITY.md`、`SOUL.md`、`USER.md`、`MEMORY.md`、`transcript.jsonl`。
- REPL 空闲主动回合在原型中为 **inner_tick**：写入合成 user 行（`inner_tick=true`），且不触发记忆管线（与 `repl_online_ack` 等合成行规则一致）。
- 渠道接入只允许通过统一 turn pipeline，不允许旁路写 `transcript.jsonl`。

## 4. 分阶段实施计划

### Phase 0 - 契约冻结与基线（先做）

- 冻结契约：
  - turn input/output
  - transcript 行结构（含 `uuid`/`trace_id`）
  - tool call envelope
  - inner_tick / repl_online_ack 等 synthetic turn 规范
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

- 并入 `research/memory_prompt_benchmark` 与 `prompt_layer`
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
| `research/memory_prompt_benchmark` | `evaluation/memory_trigger/*` | 评测工具化 | P1 |
| `prompt_layer` | `prompting/versioning/*` | 轻量接入 | P1 |
| `voice_chat` | `bridges/voice_webrtc/*` | 接口抽象后并入 | P1 |
| `gemini_native_audio_websocket_demo` | `bridges/voice_ws/*` | 重连策略与会话管理复用 | P1 |
| `s2s` | `bridges/voice_terminal/*` | 保留为调试通道 | P1 |
| 其余外围目录 | `integrations/*` 或保持独立 | 延后 + feature flag | P2 |

## 5.1 兼容策略（旧入口 -> 新入口）

| 兼容项 | 旧路径/旧命令 | 新路径/新命令 | 过渡策略 |
|---|---|---|---|
| core_v2 CLI | `python -m experimental.perpetual_agent.core_v2.main ...` | `python -m tools.inty_v2_repl.core_v2.main ...` | 保留旧 CLI shim，两版本并行 2 个里程碑后移除 |
| Telegram loop | `experimental/perpetual_agent/telegram_*` | `experimental/inty_v2_text_chat_prototype/bridges/telegram_*` | 旧模块转发到新模块并打印 deprecation 日志 |
| 语音 websocket | `experimental/gemini_native_audio_websocket_demo/*` | `experimental/inty_v2_text_chat_prototype/bridges/voice_ws/*` | 先镜像接口，再切默认入口 |
| voice chat server | `experimental/voice_chat/server/*` | `experimental/inty_v2_text_chat_prototype/bridges/voice_webrtc/*` | 先共享协议层，后迁移运行入口 |
| tool benchmark | `research/memory_prompt_benchmark/*` | `experimental/inty_v2_text_chat_prototype/evaluation/*` | 保留旧脚本，结果目录统一到新路径 |

## 6. 测试与验收矩阵

### 6.1 每阶段通用验收

- 功能验收：
  - reactive turn 正常
  - inner_tick（空闲主动）回合正常
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

### 6.3 命令级 Gate（进入下一阶段前必须通过）

- Phase 0 Gate
  - `pytest -q experimental/inty_v2_text_chat_prototype/tests/test_transcript_for_llm_turn.py`
  - `pytest -q experimental/inty_v2_text_chat_prototype/tests/test_inner_tick_schedule.py`
  - `pytest -q experimental/inty_v2_text_chat_prototype/tests/test_workspace_bootstrap_loop.py`
  - 通过标准：全部通过，且 `run_turn` 单写入约束相关测试无回归。

- Phase 1 Gate
  - `pytest -q experimental/agentic_ai_companion/tests/test_image_gen.py`
  - `pytest -q experimental/agentic_ai_companion/tests/test_memory_compaction.py`
  - `python -m tools.inty_v2_repl.main once --workspace experimental/inty_v2_text_chat_prototype/_ws --message "Generate an intimate role-play image where we hug near a window."`
  - 通过标准：工具触发成功，返回可用产物路径，compaction 开关行为符合预期。

- Phase 2 Gate
  - `pytest -q experimental/perpetual_agent/test_core_v2_*.py`
  - `python -m experimental.perpetual_agent.core_v2.main admin replay --since-minutes 120 --limit 10`
  - `python -m experimental.perpetual_agent.core_v2.main serve scheduler --once`
  - 通过标准：core_v2 幂等、租约、调度路径全部稳定。

- Phase 3 Gate
  - `python -m uvicorn experimental.gemini_native_audio_websocket_demo.server:app --reload --port 8765`
  - `curl http://127.0.0.1:8765/`
  - `bash experimental/voice_chat/server/start.sh`
  - 通过标准：语音 websocket 与 webRTC demo 都可启动，断连后能按策略恢复。

- Phase 4 Gate
  - `/workspace/.venv/bin/python research/memory_prompt_benchmark/tool_trigger_benchmark.py --config devops/config.yaml.dev --model "google/gemini-2.5-flash" --samples-per-case 4 --temperature 0.4 --max-completion-tokens 200 --timeout-seconds 90`
  - 通过标准：
    - `layered.trigger_rate_when_needed >= flat.trigger_rate_when_needed`
    - `layered.trigger_rate_when_not_needed < flat.trigger_rate_when_not_needed`
    - `layered.expected_tool_match_rate_when_needed >= flat.expected_tool_match_rate_when_needed`

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
- M5（P2 收敛完成）
  - P2 目录完成并入或被标记为永久独立并记录边界
  - 全部来源目录在映射清单中有闭环去向

退出条件：

- 达成 M5 后，`experimental/` 中 P0/P1 原型目录进入只读归档状态（仅保留文档与历史测试数据），新的 companion 能力只在 `inty_v2_text_chat_prototype` 迭代。
- 归档前必须完成文档同步检查：
  - `README.md` 迁移指引
  - `AGENTS.md` 路径与职责更新
  - `tests/docs` 测试步骤引用路径更新

