# FR_AGENTIC_KERNEL_MODULARIZATION_RFC

## 1. 背景与目标

当前仓库在 `app/` 与 `experimental/` 中存在多套 agentic 运行时实现，能力重叠明显：

- 单轮编排（prompt 组装、历史拼接、模型调用、写回）
- 工具调用循环（tool schema、dispatch、result 回注）
- 客户端封装（OpenAI-compatible / Gemini）
- 心跳主动触达（idle 检测、backoff）
- REPL 输入复用（stdin 队列 + sleep chunk）

本 RFC 目标是：

1. 给出一版可执行的目标目录结构（不做大迁移）。
2. 定义清晰模块边界（哪些要抽象，哪些保留业务定制）。
3. 给出最小迁移顺序（小步、可回滚）。
4. 每一步明确「会改哪些文件」与「先不动哪些文件」。

## 2. 范围与非目标

### 2.1 本 RFC 覆盖

- `app/core/agent`、`app/utils/openai_client.py` 与 `experimental/*` 的运行时公共层抽取。
- 渐进式整合 `clean_prompt_system` 到生产主链路。
- 对第三方框架采取局部试点策略（先不整体替换）。

### 2.2 本 RFC 不覆盖

- 不做一次性全量重构。
- 不改 Android / Kotlin 侧 API 合同。
- 不引入新数据库表或大规模 Alembic 变更。
- 不在本阶段替换所有聊天入口为单一框架运行时。

## 3. 目标目录结构（提案）

> 说明：先以 `app/core/agentic_kernel/` 为公共内核目录；生产与原型逐步迁入。  
> 本提案兼容现有 `app/core/agent`，通过桥接层平滑过渡。

```text
app/core/agentic_kernel/
  contracts/
    turn.py                # TurnInput / TurnOutput / MessageSnapshot
    tool.py                # ToolSpec / ToolCall / ToolResult / ToolContext
    prompt.py              # PromptContext / PromptBuildInput
    heartbeat.py           # HeartbeatState / HeartbeatSignal
  providers/
    facade.py              # 统一 provider 门面接口
    openai_compatible.py   # OpenAI-compatible client wrapper
    gemini.py              # Gemini client wrapper
  tools/
    registry.py            # Tool 注册与查询
    runtime.py             # Tool loop 与执行主逻辑
    dispatchers/
      workspace.py         # workspace 文件工具分发
      media.py             # 生图/语音类工具分发（可选）
  runtime/
    turn_orchestrator.py   # 单轮编排骨架（prepare/invoke/handle/persist）
    persistence.py         # 抽象写回接口（DB / JSONL）
  prompting/
    assembler.py           # Prompt 组装骨架（顺序固定，内容由业务注入）
  heartbeat/
    engine.py              # 节奏、退避、静默判定
  repl/
    stdin_mux.py           # stdin 队列 + timer 复用封装
  observability/
    trace.py               # trace id / usage / timing 统一上报接口
  bridges/
    app_agent_bridge.py    # 与 app/core/agent 的桥接
    experimental_bridge.py # 与 experimental runtime 的桥接
```

## 4. 模块边界（必须遵守）

### 4.1 必须抽象成公共模块

1. **Turn Orchestrator 骨架**
   - 只负责编排顺序，不持有业务提示词细节。
2. **Tool Runtime**
   - 统一 tool call 解析、循环、结果回注、错误语义。
3. **Provider Facade**
   - 统一模型调用入口、trace、usage、重试策略参数。
4. **Heartbeat Engine**
   - 统一 idle/backoff/silent 判断模型。
5. **REPL Input Mux**
   - 统一 stdin 读取与心跳定时轮询基础设施。

### 4.2 必须保留业务定制（不抽象为“通用智能体”）

1. **人格与关系语义提示词内容**
   - `IDENTITY` / `SOUL` / `USER` / `MEMORY` 的产品语义保持在业务层。
2. **记忆策展策略**
   - USER/SOUL/MEMORY 的更新规则与文本规范保持业务可控。
3. **渠道策略与陪伴规则**
   - 特定业务的 proactive policy、静默策略、时段规则不下沉到通用层。

## 5. 最小迁移顺序（推荐 6 步）

## Step 0：冻结契约（文档 + 类型定义，不接主链路）

### 会改文件

- `app/core/agentic_kernel/contracts/turn.py`（新）
- `app/core/agentic_kernel/contracts/tool.py`（新）
- `app/core/agentic_kernel/contracts/prompt.py`（新）
- `app/core/agentic_kernel/contracts/heartbeat.py`（新）

### 先不动文件

- `app/core/agent/agent.py`
- `experimental/inty_v2_text_chat_prototype/*`
- `experimental/agentic_ai_companion/*`
- `experimental/perpetual_agent/*`

### 验收标准

- 新契约文件可被 import，不引入运行路径变更。

---

## Step 1：提取 Provider Facade（先复用，后替换调用）

### 会改文件

- `app/core/agentic_kernel/providers/facade.py`（新）
- `app/core/agentic_kernel/providers/openai_compatible.py`（新）
- `app/core/agentic_kernel/providers/gemini.py`（新）
- `app/utils/openai_client.py`（改：向后兼容转调 facade）
- `experimental/agentic_ai_companion/clients.py`（改：转调 facade）
- `experimental/inty_v2_text_chat_prototype/client.py`（改：转调 facade）

### 先不动文件

- `app/core/agent/agent.py` 的聊天主逻辑
- `app/services/live_chat_service.py` 的会话状态机

### 验收标准

- 现有调用点不改业务行为，仅客户端初始化入口收敛。

---

## Step 2：提取 Tool Runtime（统一 tool loop）

### 会改文件

- `app/core/agentic_kernel/tools/registry.py`（新）
- `app/core/agentic_kernel/tools/runtime.py`（新）
- `app/core/agentic_kernel/tools/dispatchers/workspace.py`（新）
- `app/core/agentic_kernel/tools/dispatchers/media.py`（新，可先最小实现）
- `experimental/agentic_ai_companion/tools.py`（改：ToolDefinition 保留，loop 转 runtime）
- `experimental/inty_v2_text_chat_prototype/workspace_init_tools.py`（改：dispatch 转 runtime）
- `app/core/agent/agent.py`（改：官方助手工具循环可先桥接）

### 先不动文件

- `experimental/perpetual_agent/core_v2/*`（计划/事件编排先不并入）
- `app/services/memory_*`（记忆业务规则先不动）

### 验收标准

- 三处工具循环都能走统一 runtime，工具行为等价。

---

## Step 3：提取 Turn Orchestrator 骨架（先 experimental，后 app）

### 会改文件

- `app/core/agentic_kernel/runtime/turn_orchestrator.py`（新）
- `app/core/agentic_kernel/runtime/persistence.py`（新）
- `app/core/agentic_kernel/bridges/experimental_bridge.py`（新）
- `experimental/inty_v2_text_chat_prototype/orchestrator.py`（改：调用骨架）
- `experimental/agentic_ai_companion/async_repl.py`（改：调用骨架）

### 先不动文件

- `app/core/agent/agent.py` 的 DB 写入路径（暂保留）
- `app/services/chat_service.py` / `chat_history_service.py`

### 验收标准

- experimental 两条线先完成编排骨架复用，不影响生产路径。

---

## Step 4：整合 Prompt Assembler（清理 review-only 状态）

### 会改文件

- `app/core/agentic_kernel/prompting/assembler.py`（新）
- `app/core/agent/clean_prompt_system.py`（改：桥接到 assembler）
- `app/services/agent_service_clean.py`（改：从实验状态转生产可用）
- `app/core/agent/agent.py`（改：减少内嵌 prompt 分支）

### 先不动文件

- `experimental/inty_v2_text_chat_prototype/prompts.py`（先作为独立业务模板）
- 记忆策略文案文件与业务规则内容

### 验收标准

- `clean_prompt_system` 不再是 review-only，生产默认走 clean path。

---

## Step 5：提取 Heartbeat + REPL Mux（统一基础设施）

### 会改文件

- `app/core/agentic_kernel/heartbeat/engine.py`（新）
- `app/core/agentic_kernel/repl/stdin_mux.py`（新）
- `experimental/agentic_ai_companion/heartbeat.py`（改：转调 engine）
- `experimental/inty_v2_text_chat_prototype/main.py`（改：转调 stdin_mux）
- `app/core/repl_input/stdin_queue.py`（改：兼容导出）
- `app/core/repl_input/sleep_chunk.py`（改：兼容导出）

### 先不动文件

- `app/services/live_chat_service.py`（WS 语音链路与 heartbeat 无关）
- `experimental/perpetual_agent/channel_inbox.py`

### 验收标准

- 两个 experimental REPL 路径共享相同输入与心跳基础能力。

---

## Step 6：局部引入 PydanticAI（仅试点 tool/runtime 层）

### 会改文件

- `experimental/inty_v2_text_chat_prototype/` 下新增 `pydanticai_runner.py`（新）
- `app/core/agentic_kernel/tools/runtime.py`（改：抽象 pydanticai backend adapter）
- 相关实验测试文档：`tests/docs/TEST_STEPS_*.md`（新增）

### 先不动文件

- `app/core/agent/agent.py` 生产主链路
- `experimental/perpetual_agent/core_v2/*` 调度核心

### 验收标准

- 仅在实验开关开启时走 PydanticAI，关闭时行为与现有 runtime 一致。

## 6. 文件改动影响矩阵（总览）

| 模块 | 新增概率 | 改动概率 | 迁移阶段 |
|---|---:|---:|---|
| `app/core/agentic_kernel/*` | 高 | 中 | Step 0-6 |
| `app/utils/openai_client.py` | 低 | 高 | Step 1 |
| `app/core/agent/agent.py` | 低 | 中 | Step 2,4 |
| `app/core/agent/clean_prompt_system.py` | 低 | 中 | Step 4 |
| `experimental/inty_v2_text_chat_prototype/*` | 低 | 中高 | Step 1,2,3,5,6 |
| `experimental/agentic_ai_companion/*` | 低 | 中 | Step 1,2,3,5 |
| `experimental/perpetual_agent/core_v2/*` | 低 | 低 | 暂不动 |

## 7. 风险与回滚策略

### 7.1 主要风险

1. 工具循环统一后，某些工具的上下文注入差异导致行为漂移。
2. 客户端封装统一后，trace / timeout / provider headers 可能不一致。
3. prompt 路径收敛时，官方助手分支行为回归风险较高。

### 7.2 回滚策略

- 每一步独立 PR 与独立开关，失败可逐步回滚。
- 保留旧入口函数（deprecated 标记）至少两个迭代周期。
- 在 experimental 先试点，稳定后再推进 `app` 主路径。

## 8. 开发与评审约束

1. 每一步只做单一职责改动，不混入业务策略重写。
2. 每一步必须提供最小可执行验证（单元或脚本级）。
3. 没有覆盖验证前，不切生产默认路径。
4. 禁止将「关系语义规则」抽象成通用模板引擎逻辑。

## 9. 本 RFC 的执行优先级建议

1. Step 0 -> Step 1（低风险、高收益）
2. Step 2 -> Step 3（先实验线统一运行时）
3. Step 4（生产 prompt 路径收敛）
4. Step 5（基础设施统一）
5. Step 6（PydanticAI 局部试点）

---

本 RFC 作为后续「公共内核抽取」执行依据。若某步与当前业务目标冲突，以「先稳定生产路径、再统一实验路径」为优先。
