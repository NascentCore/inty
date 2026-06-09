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

**执行清单**：[REFACTOR_PLAN_PHASE3_SLICES.md](./REFACTOR_PLAN_PHASE3_SLICES.md)（一 slice 一 PR；单 PR ≤35 files）。

#### Phase 3.0：迁移规则

- 先盘点 `app/core/companion_harness/companion/` 与对应测试，给每个文件确认唯一目标层；不把旧 `companion/` 当作长期 namespace 保留。
- 每个切片只做同一层的 `git mv`、import 更新、测试路径更新、局部测试；切片之间不夹带行为重写。
- **一 slice merge 后再开下一分支**；禁止多切片积压在单 PR（见切片文档硬约束）。
- 每个新增或迁移后的 Python package 都补齐 `__init__.py` 包级 docstring；`__init__.py` 不放 re-export。
- 包内资源读取必须同步改成新 package 路径，尤其是 prompt markdown、workspace template seed、工具 schema 相关路径。
- import 替换用模块全路径 allowlist；勿对测试 helper 文件名做子串替换。
- 每个切片完成后搜索旧路径引用：`app.core.companion_harness.companion`、`companion/`、`tests/app/core/companion_harness/companion`。

#### Phase 3.1：拆出 `memory/`

- 迁移 MemoryStore 及其边界：`memory_store.py`、`memory_registry.py`、`memory_store_scope.py`、`memory_store_document_mapping.py`、`dreaming_consolidation.py`、`memory_taxonomy.py`、`file_store.py`。（Phase 3.1 **大部分完成**；`memory_pipeline` 已移除。）
- 迁移与长期记忆强绑定的 transcript / document 辅助逻辑；若文件同时服务 runtime，由调用方向 `memory/` 依赖，不反向依赖 runtime。
- 迁移 `templates/` 中作为 workspace 初始记忆种子的文档，并更新 `load_template_seed_text` 的资源读取。
- 同步移动 `test_memory_*`、`test_transcript_compaction.py`、记忆管线相关测试到 `tests/app/core/companion_harness/memory/`。
- 切片验收：MemoryStore 读写、registry key、document kind mapping、template seed、transcript compaction 测试通过。

#### Phase 3.2：拆出 `system_hierarchy/`

- 迁移固定 system 层级资源：`prompts/AXIOM.md`、`BOOTSTRAP.md`、`TOOLS.md`、`SIGNIFICANCE_PERCEPTION.md` 与 `prompts/system_messages.py`。
- 迁移 prompt 组装与切片：`prompt_slices.py`、`prompt_stack.py`、`ai_private_prompt.py`、`dual_llm_chat_branch_envelope.py`。
- 收敛现有 `prompting/` 过渡包；最终 system message 组装真源只保留在 `system_hierarchy/`。
- 同步移动 `test_prompts.py`、`test_prompt_stack.py`、`test_ai_private_prompt.py`、`test_significance_perception_envelope.py`。
- 切片验收：AXIOM 首条注入、bootstrap prompt 读取、TOOLS contract、significance envelope 解析与前台/后台注入测试通过。

#### Phase 3.3：拆出 `tools/`

- 迁移工具契约与执行面：`tools.py`、`companion_tool_runtime.py`、`tool_background.py`、`tool_bg_routing.py`、`openai_tools_prepare.py`。
- 迁移工具实现与工具侧辅助：`read_web_page.py`、`google_web_search.py`、`fal_z_image_tool.py`、`image_gate.py`、`runtime_inspect_tool.py`、`runtime_inspect_context.py`。
- 对齐已存在的 `tools/runtime.py`、`tools/registry.py`、`tools/dispatchers/`，避免并存两套工具注册入口。
- 同步移动 `test_tools.py`、`test_tool_*`、`test_openai_tools_prepare.py`、`test_read_web_page_tool.py`、`test_image_gate_generated_meta.py`、`test_companion_runtime_inspect_tool.py`。
- 切片验收：OpenAI tool schema、tool background transcript、runtime inspect、媒体/搜索工具测试通过。

#### Phase 3.4：拆出 `runtime/`

> **进行中**：`runtime/dreaming_batch.py`（#3301）已落地；turn / manager / session 仍在 `companion/`。切片见 [REFACTOR_PLAN_PHASE3_SLICES.md](./REFACTOR_PLAN_PHASE3_SLICES.md) S1–S3c。

- 迁移一轮对话编排：`turn.py`、`turn_engine.py`、`turn_pipeline.py`、`turn_routes.py`、`manager.py`、`websocket_coordinator.py`、`schedule_queue.py`。
- 迁移运行时事件、消息格式与 session 模型：`runtime_events.py`、`llm_runtime_events.py`、`message_format.py`、`models.py`、`utc.py`。
- 迁移运行期 LLM 调用包装中不属于 provider / llm port 的部分：`llm_chat_runtime.py`、`llm_client.py`、`llm_inference_errors.py`、`langsmith_parent_policy.py`。
- 迁移 bootstrap 运行流程：`bootstrap_user_interactive.py`；体验配置真源仍在 `experience_profile/`。
- 同步移动 `test_turn*`、`test_websocket_coordinator.py`、`test_schedule_queue.py`、`test_models.py`、`test_companion_llm_client.py`、`test_llm_runtime_events.py`、`test_bootstrap_user_interactive.py`。
- 切片验收：`run_turn`、dual-LLM 前台/后台、WebSocket coordinator、schedule queue、LangSmith parent policy 测试通过。

#### Phase 3.5：拆出 `environment/`

- 迁移环境刺激入口：`heartbeat.py`、`inner_tick_schedule.py`、`implicit_signal_messages.py`。
- 将 LivingSphere / TechnoCore 触发到 companion turn 的适配边界归入 `environment/`；运行编排仍由 `runtime/` 承接。
- 同步移动 `test_heartbeat.py`、`test_inner_tick_schedule.py`、`test_implicit_signal_messages.py`、`test_living_sphere_runtime.py`、`test_techno_core_runtime.py`。
- 切片验收：maintenance inner tick、proactive chat heartbeat、implicit signal prompt 注入、LivingSphere / TechnoCore runtime 测试通过。

#### Phase 3.6：清空旧 `companion/`

- 迁移或删除 `companion/AGENTS.md`，把仍有效的层级说明拆到新 package 或 `docs/companion_harness/`。
- 全仓替换生产代码、测试、文档、skills、REPL 对旧 `companion/` 子包的引用。
- 删除空的 `app/core/companion_harness/companion/` 与 `tests/app/core/companion_harness/companion/`。
- 切片验收：全仓无 `app.core.companion_harness.companion` import；`pytest tests/app/core/companion_harness` 通过。

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
