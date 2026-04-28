# iMate / Agentic Companion：概念架构

面向 **Android iMate** 与后端 **Agentic Companion Kernel** 对齐的阅读材料：描述客户端经 WebSocket 与 `run_turn`、上游 LLM 之间的**概念关系**（不展开实现细节）。

- 代码入口：`app/api/v1/endpoints/chat.py`（`/api/v1/chat/ws`）、`app/services/companion_chat_service.py`、`app/core/agentic_kernel/companion/turn.py`
- 契约与集成清单：[`docs/FR_INTY_V2_CHAT_WS_INTEGRATION_PLAN.md`](../FR_INTY_V2_CHAT_WS_INTEGRATION_PLAN.md)
- API 行为摘要：[`app/api/ENDPOINTS.md`](../../app/api/ENDPOINTS.md)

启用异步双路（Dual-LLM）时，前台 chat 先随一轮 WS 响应返回；后台 tool 侧完成后可能经**同一连接**再推送 assistant 帧；连接级队列与落库规则以前述文档为准。

```mermaid
flowchart LR
  subgraph Client["客户端"]
    App["App / REPL"]
  end

  subgraph Transport["传输"]
    WS["WebSocket\n/api/v1/chat/ws"]
  end

  subgraph API["后端 API 层"]
    WSH["chat 路由\n串行调度"]
    Sink["background_output_sink\n线程安全投递"]
    Q["连接级 Queue"]
  end

  subgraph Service["陪伴编排"]
    CCS["companion_chat_service"]
    CM["CompanionManager"]
  end

  subgraph Kernel["Agentic Companion Kernel"]
    RT["run_turn\n路由选择"]
    subgraph LLMPaths["LLM 语义路径"]
      CH["chat 路\n前台回复"]
      TL["tool 路\n工具循环"]
      IT["inner_tick 路"]
    end
  end

  subgraph Providers["模型网关"]
    GW["OpenAI-compatible\nchat_llm_base_url"]
  end

  App <-->|JSON 帧| WS
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
  TL -.->|ToolOutputEvent| Sink
  Sink --> Q
  Q -.->|同连接补发 assistant| WSH
```
