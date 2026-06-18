# Glossary

- MemoryStore: The mechanism of persisting a lice of memory.
  It provides a file-system path addressing with semantic naming in the components.
  - MemDoc: The data type representing a lice of memory. It has path in MemoryStore.
    We call it Doc/Document because they have to be human readable.
    They manifested into whatever responses LLM gave when being assembled into Prompt of LLM calls.

## 参照系

| 术语 | 英文别名 | 定义 |
|------|----------|------|
| **智能体（侧）** | agent side | 以 Inty companion 内核为界：**意图理解、记忆、工具、多轮编排、产出助手语义** 等逻辑归属；可含编排层。是否包含「进入单轮编排之前的连接解析与校验」须在具体文档中单点约定，否则「上行止于何处」易分歧。 |
| **客户侧** | customer-facing side | 智能体边界之外、**为送达给人** 而存在的整条链的统称：含 **App/浏览器（客户端）**、**App 业务与 UI/UX**、以及 **交付路径上的中间设施**（如连接、进程内业务下行缓冲与发送泵）。其中部分设施**物理上在服务端进程内**，语义上属「面向客户侧的交付缓冲」。 |
| **客户端** | client app | **客户侧**子集：运行在用户设备上的 **App/浏览器进程** 及其本地逻辑；**不包含** 服务端上的业务下行队列，除非显式写「逻辑上的客户端消费方」。 |

## 方向（以智能体为锚）

| 术语 | 英文别名 | 定义 |
|------|----------|------|
| **上行** | uplink | **客户侧 → 智能体** 的输入：用户消息、控制/注册帧（如签入）、时间上下文等，经解析、校验、合并后进入编排/内核的边界。 |
| **下行** | downlink | **智能体 → 客户侧** 的输出：最终要到达人或到达 App 处理逻辑的内容与包装。工程上常再分子类（见下）。 |

## 下行子类（建议区分时使用）

| 术语 | 定义 |
|------|------|
| **对话下行** | 承载 **助手语义** 的业务载荷（含与一轮对话相关的主助手回复，以及 **后台工具补帧** 等落库/展示用回复）。 |
| **信令下行** | **连接/会话层** 的短响应（如心跳、上下文确认、各类确认帧），**不等于**模型「说话」；可与对话下行共用同一 WebSocket，但**未必**经与助手业务帧相同的出站序列化路径。 |

## 传输与编排（易混词）

| 术语 | 定义 |
|------|------|
| **Companion Harness** | companion's agentic runtime |
| **Memory doc** | memory document | MemoryStore 中持久化的文档（多为 ``.md`` / ``.jsonl``）；人类可读、可 SQL 检视；persistable prompt slice 的真源。见 [MEMORY_STORE.md](./MEMORY_STORE.md#memory-doc-与-prompt-slice)。 |
| **Prompt slice** | prompt slice | 当轮注入 LLM 的 system 文本块；可 1:1 来自 Memory doc，也可仅来自包内模板或 Python 组装。 |
| **业务 outbound 队列** | 服务端上 **按序发出助手/业务类下行 JSON** 的缓冲与泵；属**客户侧交付路径**上的服务端设施。 |
| **后台事件队列（tool）** | 工具线程产出的结构化事件，经线程安全入口进入与读循环协作的队列，再组装为对话下行并入 **业务 outbound 队列**。 |
| **当轮上下文表（foreground pending）** | 按 **当轮用户消息标识** 关联工具收尾与当轮会话/语音等上下文的侧车结构；**不是**通用消息总线，也**不是**「前台」那次对话模型调用本身。 |

## 单轮执行（有工具时）

| 术语 | 英文别名 | 定义 |
|------|----------|------|
| **前台** | foreground chat | 当轮 **必须等待完成** 的对话模型调用（**不挂工具 API**），定下 **主** 用户可见话术与 **主对话下行**。 |
| **后台工具** | tool background | 前台返回后 **另线程** 执行的工具与慢思考；**不阻塞**主轨；允许 **不向用户展示** 的收尾整理。 |
| **前台预算** | foreground timeout | 仅限制 **前台** 那次模型调用的最长等待（用户轮与内在节拍可配置不同秒数）；**不含**整个后台工具线程耗时。 |

## 节拍与模式（companion 专用）

| 术语 | 定义 |
|------|------|
| **Inner-tick** | 用户空闲时的**合成轮次**（主动搭话、定时提醒、维护整理等）。实现见 `inner_tick_schedule.py` / `agentic_companion/session.py`；架构见 [DESIGN.md](/docs/companion_harness/DESIGN.md)。 |
| **Proactive chat rhythm** | 两次 proactive 尝试之间，自**最后 assistant 时间戳**起至少等待的 quiet 时长；由真实用户消息间隔自适应，默认约 30–60s。不是 worker poll 周期本身。 |
| **monolog** | **非独立运行时循环**；工作记忆中「AI 自说自话」类材料，供内在节拍等注入提示时使用。代码中称为 ai_private |
| **World Engine（世界引擎）** | **计划中**：harness 作为 actor supervisor，以共享 AgentHarness 驱动 per-agent clock 的 companion 与 sub-agent；agent 间经 mailbox 交往。见 [FR_WORLD_ENGINE.md](./FR_WORLD_ENGINE.md)。 |
| **Sub-agent** | 由 companion will to existence 召唤的 shallow agent（如 firefly）；有 L1 连续性、无 user channel、行为自主。 |

## See also

- [Companion Harness Design](./DESIGN.md)
