# iMate Agentic Companion Backend Architecture

本文是 iMate 智能体伴侣后端的产品级架构入口；更细的 agentic kernel 实现索引仍保留在 [`/docs/agentic_kernel/ARCH.md`](/docs/agentic_kernel/ARCH.md)。

## 当前生产链路

iMate App 的长期伴侣对话只在 **`/api/v1/chat/ws` WebSocket** 路径启用 agentic companion：`app/api/v1/endpoints/chat.py` 解析鉴权、控制帧和聊天帧后，以 `chat_route="websocket"` 调用 `app/services/companion_chat_service.py`，再进入 `CompanionManager` 与 `app/core/agentic_kernel/companion/turn.py::run_turn`。

生产内核的权威状态不是磁盘 workspace，而是 **SessionBinding** `(user_id, companion_id, chat_id)` 下的 **SessionCorpus**：`IDENTITY.md`、`SOUL.md`、`USER.md`、`MEMORY.md`、`context.json`、`transcript.jsonl`、运行时事件等逻辑文档经 `MemoryStore` 读写；启用 PostgreSQL repository 时写入 `companion_memory_document_versions` 的 append-only 版本表，读取当前 head。

一轮回合被拆成三个边界：

1. **Transport / API adapter**：WebSocket 负责鉴权、订阅用量、`chat_history`、错误映射、业务下行 FIFO、后台 tool 事件汇合；连接内状态收敛在 `CompanionWebSocketCoordinator`。
2. **Companion turn kernel**：`run_turn` 负责加载 SessionCorpus、组装 prompt、选择路由、调用 LLM、启动可选后台 tool、写 transcript、调度记忆管线。
3. **Durable memory / side effects**：`MemoryStore`、memory pipeline、runtime events、tool outputs 和 chat_history 分别承担可重启恢复或运营排障所需的持久化。

## 回合架构

`run_turn` 的目标阶段合同是：

```text
normalize_input
  -> load_state
  -> assemble_prompt
  -> resolve_route
  -> execute_route
  -> persist_turn
  -> schedule_memory
  -> build_result
```

当前已新增 [`turn_pipeline.py`](/app/core/agentic_kernel/companion/turn_pipeline.py) 固化前三个阶段的窄合同：

- `CompanionTurnRuntimeFlags`：归一化 inner tick、proactive heartbeat、implicit sign-on 等输入标签。
- `CompanionTurnLoadedState`：一次回合从 MemoryStore 读取的 `ContextMeta`、`PromptBundle`、transcript 窗口和 compaction 轮次。
- `CompanionTurnPromptPlan`：本轮 tools、system messages、route mode、最终 LLM messages、是否使用 dual structured chat。

这一步不改变行为；它把 `run_turn` 前半段从隐式局部变量集合收束成可测试、可迁移的阶段快照，为后续拆 `execute_route`、`persist_turn` 和 `schedule_memory` 留出稳定接口。

## 路由与实时性

| 路由 | 触发 | 行为 |
| --- | --- | --- |
| `CHAT_ONLY_SYNC` | 普通聊天且本轮无 tools | 单次 chat completion；可用 dual structured envelope 解析用户可见回复与重要性评分。 |
| `ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL` | 本轮有 tools | 前台无 tools 先返回 envelope；后台 tool 线程随后执行工具链，并通过 WebSocket 同一业务 FIFO 补 `tool_bg` assistant 帧。 |
| `HEARTBEAT_SYNC` | proactive heartbeat inner tick | 合成用户标记驱动主动轻触达，不启用 tools。 |
| `INNER_TICK_SYNC` | maintenance inner tick | 合成内在维护轮，可使用受限 inner-tick tools，不走普通记忆更新管线。 |

前台 chat 与后台 tool finish 共用 dual-LLM JSON envelope（`user_facing_reply`、`output_to_user`、三项 `importance_*` 分数）；解析边界集中在 `significance_perception.py` 与 `tool_bg_routing.py`，避免 provider reasoning 通道泄漏成用户可见文本。

## 架构判断

- **正确边界**：agentic companion 不是 legacy HTTP completions，也不是通用 `runtime/TurnOrchestrator`；生产入口以 WebSocket companion path 为准。
- **当前主要风险**：`run_turn` 仍承担执行、持久化和记忆调度，后续应继续按阶段合同向 `execute_route` / `persist_turn` / `schedule_memory` 收敛，而不是引入一个虚构的全局 kernel queue。
- **术语方向**：对外架构使用 SessionBinding / SessionCorpus / DurableSidecar / ProcessPrivate；代码中残留的 workspace/path/file 是适配层或历史命名，不应继续作为范式中心。
