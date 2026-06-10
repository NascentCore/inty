# Companion Harness 重构计划（目标架构）

> **Generated entirely by Cursor Cloud Agent** — 2026-06-10。由 `review-ideal-architecture` 从 [ARCH.md](./ARCH.md)、[FR_WORLD_ENGINE.md](./FR_WORLD_ENGINE.md)、包 `__init__.py` 与当前代码快照综合得出。差距审查见 [ARCHITECTURE_DELTA.md](./ARCHITECTURE_DELTA.md)。

## 非目标

- 不定义新 DB schema（见 [MEMORY_STORE.md](./MEMORY_STORE.md)）
- 不覆盖 Gemini Live audio 路径
- 不实现 World Engine Phase 2（sub-agent spawn）在本计划内
- 不追求生产级安全、商业化、水平扩展

## 目标包树

```
app/core/companion_harness/
├── contracts/       # Turn 级 Pydantic 契约（TurnInput/TurnOutput）；跨层唯一 turn 语义
├── memory/          # MemoryStore、registry、scope paths、transcript、dreaming consolidation
├── prompting/       # PromptBundle + system message 组装（唯一主入口）
├── llm/             # ModelGateway：SDK 封装、超时、重试、LangSmith
├── providers/       # OpenAI-compatible / Gemini 客户端工厂
├── tools/           # tool schema、runtime、tool_background、dispatchers
├── runtime/         # turn orchestration、inner-tick 调度、session 入口、dreaming batch
├── channels/        # transport adapter seam（WS coordinator 等）；不含 companion 人格语义
└── companion/       # 收敛为 domain 值对象：CompanionScope、ChatMessage、bootstrap 策略
```

`environment/`（LivingSphere / TechnoCore 世界事件 reader）在 World Engine Phase 1 之后从 `techno_core` / `living_sphere` 经 seam 接入，**不在本 Phase 3 包拆分内**。

## 依赖矩阵

| From | May import | Must not import |
| --- | --- | --- |
| `contracts/` | （无 harness 内依赖） | 任意 harness 子包 |
| `memory/` | `contracts/` | `runtime/`, `companion/turn*`, `app.services`, `app.api` |
| `prompting/` | `memory/`, `contracts/` | `runtime/`, `tools/` |
| `llm/` | `providers/`, `contracts/` | `companion/`, `runtime/`, `tools/` |
| `providers/` | `app.utils`（config） | `companion/`, `runtime/` |
| `tools/` | `memory/`, `llm/`, `prompting/`, `contracts/` | `companion/turn*`, `app.api` |
| `runtime/` | `memory/`, `llm/`, `tools/`, `prompting/`, `contracts/`, `channels/` | `app.api` |
| `channels/` | `runtime/`, `contracts/` | `companion/turn*`, `memory/` 写路径 |
| `companion/` | `contracts/` | `runtime/`（迁完后仅 domain types） |

应用层 `app/services/agentic_companion/` 与 `app/api/v1/endpoints/chat_ws.py` 只依赖 `channels/` + `runtime/` 对外 seam，不反向被 harness import。

## 阶段

| Phase | 内容 | 验收 |
| --- | --- | --- |
| **3.1** `memory/` 独立 | `scope`、`ChatMessage`、`utc` 迁入 `memory/` 或 `contracts/`；消除 `memory → companion` | `rg 'memory.*companion\.(scope|models|utc)' app/core/companion_harness/memory` 零命中 |
| **3.2** `llm/` ModelGateway | 合并 `CompanionLLMClient`、`llm_chat_runtime`、`create_chat_completion_sync` 为单一 chokepoint | `rg 'CompanionLLMClient\|create_chat_completion_sync' app/core/companion_harness` 仅 `llm/` |
| **3.3** `prompting/` 单入口 | `prompt_stack` + `system_messages` 迁入；`turn.py` dual-LLM 路径经 `prompt_stack` | `rg 'build_system_messages_for_' app/core/companion_harness/companion/turn.py` 零命中 |
| **3.4** `runtime/` turn 编排 | `turn*`、`manager`、`inner_tick_schedule`、`proactive_chat`、`schedule_queue`、`dreaming` 域编排迁入 | `companion/` 不含 `turn.py`、`manager.py` |
| **3.5** `channels/` transport | `websocket_coordinator` 迁出；`inner_tick_fire` 不再 import `app.api` | `rg 'from app\.api' app/core/companion_harness` 零命中 |
| **3.6** `contracts/turn` 接线 | `run_turn` 边界使用 `TurnInput`/`TurnOutput` | `contracts/turn.py` 被 `runtime/` import |
| **4.x** World Engine spine | 共享 AgentHarness（见 FR_WORLD_ENGINE §2） | 独立 epic |

## See also

- [ARCHITECTURE_DELTA.md](./ARCHITECTURE_DELTA.md) — 设计 vs 实现差距（本次审查）
- [ARCH.md](./ARCH.md) — 生产架构与不可变约束
- [REFACTORING_PLAN.md](./REFACTORING_PLAN.md) — 历史占位；以本文为准
