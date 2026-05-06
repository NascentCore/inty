# iMate / Agentic Companion：概念架构

面向 **Android iMate** 与后端 **Agentic Companion Kernel** 对齐的阅读材料：描述客户端经 WebSocket 与 `run_turn`、MemoryStore、工具循环、上游 LLM 之间的**当前概念关系**。本文不替代 API 文档；读者应先用本页判断生产链路、实验脚手架与可改进边界，再进入源码。

- 生产代码入口：`/app/api/v1/endpoints/chat.py`（`/api/v1/chat/ws`）、`/app/services/chat_websocket_session.py`、`/app/services/companion_chat_service.py`、`/app/core/agentic_kernel/companion/manager.py`、`/app/core/agentic_kernel/companion/turn.py`
- 内核目录说明：`/app/core/agentic_kernel/companion/README.md`
- API 行为与 WS 约定：`/app/api/ENDPOINTS.md`

启用异步双路（Dual-LLM）时，前台 chat 先随一轮 WS 响应返回；后台 tool 侧完成后可能经**同一连接**再推送 assistant 帧；连接级队列与落库规则以前述文档为准。

**分层（传输 vs 逻辑）**：WebSocket 在 **repl/client 与 agent 的逻辑会话之下**。同一 TCP/WebSocket 连接上：

- **传输层 / 连接确认**：ping、pong、`client_context_ack` 等由路由 **直接** `send_json`，不入队；仅表示链路存活与时间上下文校验。
- **逻辑层 / 对话下行**：发往客户端的助手业务 JSON（foreground、tool 异步补帧、kickoff、HTTP 映射错误帧）经 **`asyncio.Queue`** + **`chat_ws_outbound_pump`**（`/app/services/chat_websocket_session.py`）FIFO `send_json`，与 REPL 客户端侧约定的 agent 对话顺序一致。

**REPL 客户端队列（`/tools/inty_v2_repl`）**：上行用户帧 `post_turn`（`/tools/inty_v2_repl/backend_chat_ws.py`）仅 `ws.send`，在 **WebSocket/TCP 发送侧 FIFO** 排队（服务端仍按连接串行处理对话）；下行助手与错误 JSON 由 recv 协程写入 **`_response_q`**（`asyncio.Queue`），终端经 `pop_downlink_item`（`/tools/inty_v2_repl/repl_message_io.py`）非阻塞取出。

**队列中心化下行（inty-ws）**：生产路径 `/api/v1/chat/ws` 使用上述队列与 pump。**`/ws/verify`** 也使用同一套 queue + pump（与 `/ws` 一致的业务 FIFO），但每帧仅做一次最简 `chat.completions`（system + user），不经 Agent runtime / companion；不落 chat_history（详见 `chat_completions_websocket_verify` docstring）。

**逻辑架构（消息路径）**：先约定逻辑名称（与实现符号不必一一同名），再按**消息传递方向**画图。


| 逻辑名                      | 含义                                                                       |
| ------------------------ | ------------------------------------------------------------------------ |
| **用户**                   | 人机边界                                                                     |
| **repl**                 | REPL 会话壳：内含 **repl message-queue** 与两个消费者                                |
| **repl message-queue**   | 收集并暂存：**用户输入**、**经 WS 下行的 agent 侧消息**                                    |
| **repl_tui**             | 从 repl message-queue **取出 agent 消息**，驱动 **TUI** 呈现给用户                    |
| **repl_ws_egress**       | 从 repl message-queue **取出用户消息**，封装为 **上行 WS 帧**                          |
| **ws_transport**         | **WebSocket 全双工管线**：只做比特/帧级双向搬运，**不含**回合语义                               |
| **agentic_kernel**       | 编排壳：内含 **kernel message-queue** 与四个方向的适配                                 |
| **kernel message-queue** | 收集并暂存：**经 WS 来自用户的消息**、**经 llm_runtime 来自 LLM 的消息**（含多轮/异步帧时在逻辑上仍汇总为此队列） |
| **kernel_ws_ingress**    | 从 ws_transport **接收用户向消息**，**注入** kernel message-queue                   |
| **kernel_llm_ingress**   | 从 **LLM API** 侧 **接收模型输出**，**注入** kernel message-queue                   |
| **kernel_llm_egress**    | 从 kernel message-queue **取出**待推理上下文，交给 llm_runtime                       |
| **kernel_ws_egress**     | 从 kernel message-queue **取出**待发助手帧，送到 ws_transport                       |
| **llm_runtime**          | **提示词拼接** + **LLM inference 调用**（对 kernel 暴露「一次调用」边界）                    |
| **LLM API**              | 外部模型服务                                                                   |


下图箭头均为**消息**流向（谁写入谁、谁读出谁）；控制帧、鉴权、队列泵等实现细节见上文「分层」与下一张实现细化图。

```mermaid
flowchart TB
  User["用户"]

  subgraph repl["repl"]
    RMQ["repl message-queue"]
    ReplTui["repl_tui\n(agent 消息 -> TUI)"]
    ReplWsOut["repl_ws_egress\n(用户消息 -> WS 帧)"]
    RMQ -->|"取出 agent 消息"| ReplTui
    RMQ -->|"取出用户消息"| ReplWsOut
  end

  User -->|"用户输入"| RMQ
  ReplTui -->|"呈现"| User

  WST["ws_transport\n(WebSocket 全双工管线)"]

  ReplWsOut -->|"上行帧"| WST
  WST -->|"下行帧"| RMQ

  subgraph kernel["agentic kernel"]
    KMQ["kernel message-queue"]
    KwIn["kernel_ws_ingress"]
    KlIn["kernel_llm_ingress"]
    KlOut["kernel_llm_egress"]
    KwOut["kernel_ws_egress"]
    WST -->|"用户向消息"| KwIn
    KwIn -->|"注入"| KMQ
    KlIn -->|"注入"| KMQ
    KMQ -->|"取出 -> 推理"| KlOut
    KMQ -->|"取出 -> 助手帧"| KwOut
    KwOut -->|"下行帧"| WST
  end

  subgraph llm_rt["llm_runtime"]
    Prompt["prompt_build\n提示词拼接"]
    Infer["llm_infer\n推理调用"]
    Prompt --> Infer
  end

  KlOut -->|"请求"| Prompt
  Infer -->|"HTTP/S 等"| LLM["LLM API"]
  LLM -->|"模型输出"| KlIn
```



**小结（逻辑图 vs 实现）**：上图为**理想化**消息路径；下表将图中要素与仓库行为逐条对照（「是否合理」指作为教学抽象是否自洽，「与代码」指是否宜按字面当作逐函数实现）。


| 图上要素                            | 是否合理   | 与代码                                              |
| ------------------------------- | ------ | ------------------------------------------------ |
| 全双工 WS 管线                       | 是      | 一致                                               |
| repl 下行：WS -> 队列 -> TUI         | 是      | 与 `_response_q` 与 `pop_downlink_item` 等 drain 一致 |
| repl 上行：队列 -> WS                | 弱      | 实为 `post_turn` 直连 `ws.send`，非从同一队列出队             |
| 单一 kernel message-queue         | 教学上可接受 | 实为 recv 路径、`outbound_queue`、`bg_queue`、进程内状态等多结构 |
| LLM 输出注入同一 kernel message-queue | 概念汇总   | 实为调用链返回与组帧，经 `outbound_queue` 等写出，非独立「先入全局队列」    |


**实现细化**：同一链路在仓库中的近似映射（路由、`run_turn`、连接级队列名），可与上表逻辑名对照。

```mermaid
flowchart LR
  subgraph repl["repl"]
    RUI["stdin /\n终端输出"]
    ROUT["message-queue\n上行缓冲\n→ socket"]
    RIN["message-queue\n下行缓冲\n← socket"]
  end

  subgraph ChatWs["/api/v1/chat/ws"]
    WS["WebSocket\nchat.py"]
    subgraph MsgIo["连接级 message-queue"]
      WIN["message-queue\n服务端入站\n用户 JSON FIFO"]
      OQ["message-queue\n服务端出站\n业务 JSON FIFO"]
      PUMP["顺序写出\n连接级 FIFO"]
    end
    WSH["_agent_chat_completions_impl\n+ recv 循环编排"]
    BGQ["message-queue\n后台汇合\ntool 异步"]
    CCS["companion_chat_service"]
    CM["CompanionManager"]
  end

  subgraph Kernel["agentic kernel"]
    RT["run_turn"]
    subgraph LLMPaths["LLM 语义路径"]
      CH["chat 路\n前台回复"]
      TL["tool 路\n工具循环"]
      IT["inner_tick 路"]
    end
    GW["OpenAI-compatible\nchat_llm_base_url"]
  end

  RUI --> ROUT --> WS --> WIN --> WSH
  WSH --> CCS --> CM --> RT
  RT --> CH
  RT --> TL
  RT --> IT
  CH --> GW
  TL --> GW
  IT --> GW
  TL -.->|ToolOutputEvent\ncompanion_bg_sink| BGQ
  BGQ -.->|wait 先到则组装 payload| WSH
  WSH -->|foreground /\nkickoff /\nHTTP 异常 /\ntool_bg payload\n一律 put| OQ
  OQ --> PUMP -->|FIFO send_json| WS --> RIN --> RUI
```



控制帧（ping/pong、client_context_ack）不经 `outbound_queue`，由 `_handle_chat_websocket_control_json` 直连 `send_json`（见上文「分层」）。上图仅描述生产 `/api/v1/chat/ws`；`/ws/verify` 共用**服务端出站 message-queue + 顺序写出**，编排为最简 `chat.completions`，不经 CCS/CM/RT。

## 生产路径与实验脚手架

`/app/core/agentic_kernel` 不是一条单一运行时流水线，而是同时包含生产 companion 内核、实验桥接层和通用基础设施。阅读目录时应按下表区分：

| 区域 | 当前角色 | 是否在生产 `/api/v1/chat/ws` 主线 |
| --- | --- | --- |
| `/app/core/agentic_kernel/companion/` | 生产 companion 内核。`CompanionManager` 负责 session 与 `MemoryStore`，`turn.run_turn` 负责 prompt、transcript、LLM 调用、工具循环、异步 tool background、记忆管线与结果返回。 | 是 |
| `/app/core/agentic_kernel/companion/README.md` | companion 工作区、版本表、`agents` 表边界、context 与提示词切片说明。 | 是，作为维护说明 |
| `/app/core/agentic_kernel/contracts/turn.py`、`/app/core/agentic_kernel/runtime/turn_orchestrator.py`、`/app/core/agentic_kernel/runtime/persistence.py` | 通用 turn contract / orchestrator 抽象。 | 否；当前只由 `/app/core/agentic_kernel/bridges/experimental_bridge.py` 使用 |
| `/app/core/agentic_kernel/bridges/experimental_bridge.py` | 把 dict history 转为 `TurnInput`，再接通通用 `TurnOrchestrator` 的实验桥。 | 否 |
| `/app/core/agentic_kernel/providers/` | OpenAI-compatible / Gemini client 工厂与缓存。 | 间接；companion 的 LLM client 会使用 OpenAI-compatible 基础设施 |

因此，文中 "agentic kernel" 在生产链路里特指 `companion/*` 这条内核路径；不要把 `TurnOrchestrator` 理解为 iMate WebSocket 当前的一轮对话编排器。

## 持久化与旧 Agent 边界

`/app/services/companion_chat_service.py` 会把 API 里的 `agent_id` 原样作为 `companion_id` 传给 `CompanionManager.get_or_create_session`。路由层仍会通过 `agents` 表校验角色与会话，但 companion 推理本身不读取 `Agent` ORM 上的 `main_prompt`、`mode_prompt`、`personality` 等旧聊天字段。

当前 companion 人设、上下文与 transcript 的权威来源是 `MemoryStore`。启用 PostgreSQL DSN 时，`IDENTITY.md`、`SOUL.md`、`USER.md`、`MEMORY.md`、`transcript.jsonl`、`context.json` 等逻辑文档写入 `companion_workspace_document_versions` 的 append-only 版本行。排查一次生产对话时，应优先用 `user_id + companion_id(=agent_id) + chat_id` 查最新 document content，再回看 `chat_history` 与 WS 下行帧。

## 架构批判

- **抽象命名有误导性**：目录级 `agentic_kernel` 同时放生产 companion、实验 `TurnOrchestrator`、provider 与工具基础设施；外部读者容易误以为生产 WS 主线已经统一到通用 orchestrator。
- **一轮对话职责过宽**：`companion/turn.py::run_turn` 同时处理 prompt stack、LLM 路由、工具循环、LangSmith trace、transcript 持久化、记忆调度、异步 background tool 汇合。它是可运行的中心点，但也是变更风险最大的耦合点。
- **队列语义分散**：生产 WS 下行有 `outbound_queue`，后台 tool 有 background sink / queue，REPL 侧有 `_response_q`，而概念图中常被压成一个 "message-queue"。这有助于教学，但在调试顺序、重连、重复发送时必须回到具体队列。
- **双写视角仍存在**：用户可见消息在 `chat_history`，companion 内核状态在 `MemoryStore` / `companion_workspace_document_versions`；两者不是一个事务边界。kickoff 或后台补帧失败时，可能出现 transcript 与用户可见历史不完全一致。

## 可落地改进

优先把生产 companion 的 "turn pipeline" 从 `run_turn` 中切出显式阶段对象或阶段函数，先只做结构性拆分，不改变行为：

1. `load_turn_context`：读取 context、prompt bundle、transcript、compaction state。
2. `build_turn_messages`：生成 system messages、用户尾帧、dual-LLM chat/tool 两套 message。
3. `execute_turn_route`：执行 foreground chat、同步 tool loop、inner tick 或 async foreground/background tool 分支。
4. `persist_turn_result`：写 transcript、trace id、significance metadata。
5. `schedule_turn_side_effects`：记忆管线与 background follow-up。

这个改进不要求把生产链路迁移到 `TurnOrchestrator`。更稳妥的目标是先让生产路径的阶段边界可测试、可观测，再决定 `TurnOrchestrator` 是否值得吸收 companion 语义。收益是降低 `run_turn` 单点复杂度，并让异步 tool、inner tick、implicit sign-on 等路线能分别添加窄测试。