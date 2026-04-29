# iMate / Agentic Companion：概念架构

面向 **Android iMate** 与后端 **Agentic Companion Kernel** 对齐的阅读材料：描述客户端经 WebSocket 与 `run_turn`、上游 LLM 之间的**概念关系**（不展开实现细节）。

- 代码入口：`app/api/v1/endpoints/chat.py`（`/api/v1/chat/ws`）、`app/services/companion_chat_service.py`、`app/core/agentic_kernel/companion/turn.py`
- API 行为与 WS 约定：[`app/api/ENDPOINTS.md`](../../app/api/ENDPOINTS.md)

启用异步双路（Dual-LLM）时，前台 chat 先随一轮 WS 响应返回；后台 tool 侧完成后可能经**同一连接**再推送 assistant 帧；连接级队列与落库规则以前述文档为准。

**分层（传输 vs 逻辑）**：WebSocket 在 **repl/client 与 agent 的逻辑会话之下**。同一 TCP/WebSocket 连接上：
- **传输层 / 连接确认**：ping、pong、`client_context_ack` 等由路由 **直接** `send_json`，不入队；仅表示链路存活与时间上下文校验。
- **逻辑层 / 对话下行**：发往客户端的助手业务 JSON（foreground、tool 异步补帧、kickoff、HTTP 映射错误帧）经 **`asyncio.Queue`** + **`chat_ws_outbound_pump`**（[`app/services/chat_websocket_session.py`](../../app/services/chat_websocket_session.py)）FIFO `send_json`，与 REPL / App 侧约定的 agent 对话顺序一致。

**队列中心化下行（inty-ws）**：生产路径 `/api/v1/chat/ws` 使用上述队列与 pump。**`/ws/verify`** 也使用同一套 queue + pump（与 `/ws` 一致的业务 FIFO），但每帧仅做一次最简 `chat.completions`（system + user），不经 Agent runtime / companion；不落 chat_history（详见 `chat_completions_websocket_verify` docstring）。

```mermaid
flowchart LR
  subgraph Client["客户端"]
    App["App / REPL"]
  end

  subgraph Transport["传输"]
    WS["WebSocket\n/api/v1/chat/ws"]
  end

  subgraph API["后端 chat 路由 chat.py"]
    WSH["recv 循环 +\n_agent_chat_completions_impl 等"]
    BGQ["bg_queue\nasyncio.Queue"]
    OQ["outbound_queue\n业务 JSON FIFO"]
    PUMP["chat_ws_outbound_pump"]
  end

  subgraph Service["陪伴编排"]
    CCS["companion_chat_service"]
    CM["CompanionManager"]
  end

  subgraph Kernel["Agentic Companion Kernel"]
    RT["run_turn"]
    subgraph LLMPaths["LLM 语义路径"]
      CH["chat 路\n前台回复"]
      TL["tool 路\n工具循环"]
      IT["inner_tick 路"]
    end
  end

  subgraph Providers["模型网关"]
    GW["OpenAI-compatible\nchat_llm_base_url"]
  end

  App <-->|JSON 业务帧| WS
  WS --> WSH
  WSH --> CCS
  CCS --> CM
  CM --> RT
  RT --> CH
  RT --> TL
  RT --> IT
  CH --> GW
  TL --> GW
  IT --> GW
  TL -.->|ToolOutputEvent\ncompanion_bg_sink| BGQ
  BGQ -.->|wait 先到则组装 payload| WSH
  WSH -->|foreground /\nkickoff /\nHTTP 异常 /\ntool_bg payload\n一律 put| OQ
  OQ --> PUMP
  PUMP -->|FIFO send_json| WS
```

控制帧（ping/pong、client_context_ack）不经 `outbound_queue`，由 `_handle_chat_websocket_control_json` 直连 `send_json`（见上文「分层」）。上图仅描述生产 `/api/v1/chat/ws`；`/ws/verify` 共用 **OQ + PUMP**，编排为最简 `chat.completions`，不经 CCS/CM/RT。
