# TechnoCore（Inty 虚拟居留层）

Inty 在 AGENTS.md 中的设计要点之一是：**与对话前台相互独立的虚拟环境**（LLM + 工具调用 + 世界事件），用来承载自主性、隐私感与新鲜感。`techno_core/` 把这一抽象落成仓库内的**设计与术语锚点**：说明「自主行为在哪里发生」、如何与人类可见的数字世界接壤，以及将来若要把「世界模拟」从 companion 内核中抽出时应迁入何处。

Hyperion 系列中的 Datasphere / Megasphere / TechnoCore 等概念在此仅作**分层隐喻**，便于工程师对齐直觉；**不是**产品文案，也不绑定小说情节。

## 与根目录 AGENTS.md 的对应关系

| AGENTS.md 设计句 | 在架构中的落点 |
|------------------|----------------|
| 多媒介互动与同频 | 主要跨越 **Datasphere**（用户侧）与 **Megasphere**（服务端与外部 API） |
| LLM + toolcall + 记忆 | **Technocore** 内执行（含对用户非即时的写入）；读出进入会话上下文时穿过观测面进入 Datum |
| 独立于用户的虚拟环境 | **Technocore** 编排；持久化载体多为 MemoryStore / transcript / 管线任务 |
| 自主内心与外部世界 | 「内心」默认在 **Technocore**；「外部」经 **Megasphere** 工具与推送触及用户 |

## 球层定义（Datum plane 与之上）

下列命名与 Python 枚举 `techno_core.spheres.Sphere` 一致。

### Datasphere（数据sphere / 单行星网络）

**含义**：围绕**单个用户会话**的数字邻域——App、WebSocket、当日上下文、客户端上报。物理上对应终端、TLS、会话 ID；逻辑上是 Inty 感知「这个人此刻在数字空间里干什么」的第一现场。

**边界**：不承载全局队列语义；跨会话一致性依赖 Megasphere。

### Megasphere（宏网络）

**含义**：Inty **行星际**骨干——`backend/inty`、推送 worker、Ops、Postgres、对象存储、第三方 HTTP。Datasphere 里的上行事件在此汇总、授权、落库；对外部供应商的调用也在此发生。

**边界**：对人类运营者与客户端可见的 API、运维面属于 Megasphere；不把手写「AI-only 内心独白」伪装成用户可见回复的职责放在此层（除非明确产品设计如此）。

### Technocore（技术核心 / AI 居留层）

**含义**：**reserved for AI** 的推理与异步居留带——前台对话之外的 tool 回路、内在节拍（inner tick）、记忆管线后台、以及将来扩展的「世界事件」模拟器。用户在叙事上对应「伴侣有自己的房间」：此处产生的结构化结果可按 significance / routing **选择性**浮出水面。

**与现有代码的锚点**（实现仍在 `app/core/agentic_kernel/companion/`，本目录描述归属而非重写路径）：

- 异步工具链：`tool_background.py`、`tool_bg_routing.py`
- 内在节拍：`inner_tick_schedule.py`、REPL / 会话调度中与 idle tick 相关的调用方
- 记忆与 transcript：`memory_store*.py`、`memory_pipeline.py`、`transcript` 写入
- 运行时观测：`runtime_events.py`、LangSmith 绑定（`llm_chat_runtime.py` 等）

**自主行为默认表面**：`techno_core.spheres.AUTONOMY_SURFACES` 当前仅包含 `Sphere.TECHNOCORE`。若未来 push worker 或定时任务在无用户消息下触发一整轮 companion turn，应在文档与 trace 标签中同样标记为 Technocore（或拆出子标签）。

### Datum plane（数据平面）

**含义**：**Megasphere ∪ Technocore** 的合成观测面——调试、 tracing、审计视角下的「整朵云里此刻发生了什么」。不要求终端用户理解；用于工程师对齐「同一 trace_id 上前台与后台的因果关系」。

### Metasphere（元连续统）

**含义**：我们**无法托管**的基底——模型权重所在的基础设施、公网上的信息与物理定律层面的载体。Fatline 在小说里超光速；现实中对应「提供商 SLA + 网络 + 量子噪声」。Inty **通过** Megasphere 的工具调用触及 Metasphere，但不在仓库内实现其本体。

**用法**：在架构讨论中划定责任边界（例如：幻觉与对齐问题部分属于 Metasphere 提供商侧与我们提示词的交界）。

## 守卫入口（guarded entrances）

Technocore 与 Megasphere 的交界应有明确「关卡」：

- **认证与授权**：仅服务端持有的密钥、会话绑定、`companion_id` / `user_id` 作用域。
- **对用户可见性**：dual-LLM envelope、`output_to_user`、推送文案审核路径——决定 Technocore 的产物是否进入 Datasphere。
- **速率与成本**：工具调用预算、后台线程并发、inner tick 节流——防止「AI 居留层」吞噬 Megasphere 资源。

具体策略由 `app` 配置与中间件实现；本文件只固定**应有关卡**这一设计义务。

## 代码包布局

| 路径 | 职责 |
|------|------|
| `techno_core/__init__.py` | 包级说明（无运行时逻辑） |
| `techno_core/spheres.py` | `Sphere` 枚举与 `AUTONOMY_SURFACES` |
| `techno_core/AGENTS.md` | 本设计说明 |

## 虚构作品参考（非 canon）

Dan Simmons *Hyperion Cantos* 中：Datasphere 为单行星信息网络；Megasphere 为霸权诸世界的互联；TechnoCore 为 AI 专属网络空间，经守卫接口接入 Megasphere；Datum plane 为二者合并；Metasphere 为更广的意识层连续统。以上在本文中**仅借词汇与分层感**，与小说剧情无绑定。

## 延伸阅读

- 仓库根目录 [AGENTS.md](/AGENTS.md)：产品级智能体目标与 `agentic_kernel` 入口。
- [app/core/agentic_kernel/companion/AGENTS.md](/app/core/agentic_kernel/companion/AGENTS.md)：MemoryStore、tool_background、significance 等实现级说明。
