# Companion Harness 重构计划

## 目标

将 `app/core/agentic_kernel/` 重构为 `app/core/companion_harness/`，把核心概念从泛化的 agent kernel 收敛为面向长期亲密关系体验的 Companion Harness。这个 harness 负责组织拟人伴侣的运行、记忆、系统层级、工具、体验配置与环境刺激接入；LLM 能力只是其内部的一层，而不是顶层命名的中心。

## 命名

- 顶层概念：Companion Harness
- 顶层代码包：`app/core/companion_harness/`
- 中文语义：伴侣拟人框架 / 伴侣工程框架
- 不再使用 `agentic_kernel` 作为核心包名。
- 不使用 `companion_runtime` 作为顶层包名；`runtime` 只表示运行层。

## 目标目录结构

- `app/core/companion_harness/runtime/`：回合编排、session、WebSocket 协调、后台任务、运行时事件。
- `app/core/companion_harness/llm/`：LLM 端口、chat completion、模型调用上下文、LangSmith enrich。
- `app/core/companion_harness/providers/`：OpenAI-compatible、OpenRouter、Gemini 等 provider。
- `app/core/companion_harness/memory/`：MemoryStore、registry、scope、document mapping、memory pipeline。
- `app/core/companion_harness/system_hierarchy/`：AXIOM、BOOTSTRAP、TOOLS、SIGNIFICANCE、prompt slices、system messages。
- `app/core/companion_harness/tools/`：工具定义、tool runtime、tool background、dispatcher。
- `app/core/companion_harness/experience/`：experience profile、bootstrap、context mode。
- `app/core/companion_harness/environment/`：LivingSphere、TechnoCore、heartbeat、inner tick、implicit signals。
- `app/core/companion_harness/contracts/`：turn contracts 与跨层 Pydantic contract。
- `app/core/companion_harness/bridges/`：实验 bridge 与外部 harness/demo 适配。

## 分阶段迁移

### Phase 1：包级搬迁

- 移动 `app/core/agentic_kernel/` 到 `app/core/companion_harness/`。
- 移动 `tests/app/core/agentic_kernel/` 到 `tests/app/core/companion_harness/`。
- 全仓替换生产代码与测试 import：
  - `app.core.agentic_kernel` -> `app.core.companion_harness`
  - `app/core/agentic_kernel` -> `app/core/companion_harness`
- 补齐 `app/core/companion_harness/__init__.py` 包级 docstring。
- 不保留长期兼容 shim。

### Phase 2：文档与工具路径收敛

- 移动 `docs/agentic_kernel/` 到 `docs/companion_harness/`。
- 更新 REPL、skills、maintenance、work log 中对旧路径的引用。
- 将文档术语统一为 Companion Harness；仅在历史说明中保留 `agentic_kernel`。

### Phase 3：拆分旧 `companion/` 子包

- `companion/memory_*` -> `memory/`
- `companion/prompts/*`、`prompt_*`、`significance_perception.py` -> `system_hierarchy/`
- `companion/tool_*`、`tools.py`、`companion_tool_runtime.py` -> `tools/`
- `companion/turn*`、`manager.py`、`websocket_coordinator.py`、`runtime_*` -> `runtime/`
- `companion/heartbeat.py`、`inner_tick_schedule.py`、`implicit_signal_messages.py` -> `environment/`
- 每拆一层同步更新测试路径与 import。

### Phase 4：验证与收尾

- 跑 `pytest tests/app/core/companion_harness`。
- 跑受影响的 WebSocket companion E2E。
- 跑一次 companion turn smoke，确认 `run_turn`、MemoryStore、tool background、prompt stack 主路径仍能贯通。
- 清理旧路径残留引用；生产代码不得再 import `app.core.agentic_kernel`。

## 不在本次重构中处理

- 不改数据库表名，例如 `companion_memory_document_versions`。
- 不改外部 API 字段名，例如 `agent_id`、`companion_id`。
- 不重写 MemoryStore 语义。
- 不调整产品体验模式，只做命名与代码组织收敛。

## 验收标准

- `app/core/companion_harness/` 是唯一核心伴侣 harness 包。
- 生产代码没有 `app.core.agentic_kernel` import。
- 对应测试目录迁移到 `tests/app/core/companion_harness/`。
- 文档中新的架构真源使用 Companion Harness 命名。
- 核心测试与 companion smoke 通过。
