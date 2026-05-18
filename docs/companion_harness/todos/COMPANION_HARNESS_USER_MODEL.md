# 下一步计划：Companion Harness 差距与伴侣用户模型

本文档由 2026-05-09 相关讨论整理，供 iMate / Companion Harness 方向排期用。设计目标真源见仓库根目录 `/AGENTS.md` 中 Agentic Companion 小节；实现真源见 `/app/core/companion_harness/`。

## 术语

### 概念内涵

- **用户模型**：智能体对「用户」这一交互对象的内部表征；该表征支撑智能体选择与用户互动的方式（内容、节奏、边界、记忆引用等）。不是「互联网空间拓扑」或「用户在哪些 App 里」alone，核心是 **对人的可交互建模**。
- **伴侣用户模型**：当「用户模型」可能与账号表 User、营销含义的「用户画像」或通用画像字段混淆时使用的全称，强调 **陪伴场景下、Companion Harness 所维护** 的那一份用户表征。

### 对内文档与代码常量约定

| 中文（优先） | English | 使用场景 |
|--------------|---------|----------|
| 用户模型 | User Model | 默认用语；注释、设计文档、非歧义代码命名 |
| 伴侣用户模型 | Companion User Model | 与 ORM User、画像产品概念并存时需消歧 |

- 默认采用：**用户模型** / **User Model**。
- 需消歧时采用：**伴侣用户模型** / **Companion User Model**。
- **不建议** 再以「用户数字空间建模」作为该概念的主标签（易被理解为虚拟空间、终端列表等，而非「对用户的建模」）。

## 相对设计目标仍缺或明显偏薄

对照 `/AGENTS.md` 中 companion 设计意图（多媒介与同频、LLM+工具+记忆、独立虚拟环境与新鲜感），相对 `/app/core/companion_harness/` 当前实现：

### 多模态内容生成与多媒介通信

- **已有**：会话型文本主链路；工具链侧图像生成与编辑（如 `generate_image` / `modify_image`）；Web 检索与读网页等。
- **仍缺或偏薄**：短信、电话、语音通话、视频通话等 **渠道** 在本包内的一等公民抽象（路由、会话绑定、与 transcript / 工具的契约）；用户侧 **多模态输入**（如用户上传音视频）若在 API 层存在，尚未与内核消息模型统一对齐。

### 与用户侧信息同频（伴侣用户模型）

- **已有**：隐式客户端信号与时间上下文（如 `/app/schemas/implicit_signals.py`、`implicit_signal_messages.py`）；工作区 `USER.md` 等人格化档案与记忆注入。
- **仍缺或偏薄**：结构化的 **伴侣用户模型**（字段、版本、置信度、更新策略）；对用户实体状态（偏好演变、关系约定、情境线索）的 **显式契约**，而非仅靠散文档案与片段信号拼接。

### LLM + 工具调用 + 记忆

- **已有**：分层记忆（情景 / 摘要 / 语义）、`transcript.jsonl`、异步工具线程、双模型路由、重要性打分（significance perception）等（详见 `/app/core/companion_harness/companion/AGENTS.md`）。
- **仍缺或偏薄**：工具后台路径对部分供应商 **仅把结构化 envelope 放在 `reasoning` / `reasoning_details`**、而 `content` 为空时的统一读取（`/app/core/companion_harness/tools/tool_background.py` 内 TODO）；**偶发 LLM 无输出** 尚未闭环（复现、降级、观测）。

### 独立虚拟环境与「世界」事件（智能体自主性与新鲜感）

- **已有**：定时提醒队列（`schedule_queue.py`）、陪伴心跳与 inner tick（`heartbeat.py`、`inner_tick_schedule.py`）等 **弱自主 / 节奏层** 机制。
- **仍缺或偏薄**：与主会话 **解耦** 的持续 **世界状态** 与 **环境事件引擎**（LLM + 工具驱动的独立演进，而非仅合成 user 行的提醒与接话）。

### 工程与边界

- **仍缺或偏薄**：`/app/core/companion_harness/__init__.py` 缺少包级 docstring（与仓库 Python 包约定不一致）。

## 谈话结论（事实摘记）

- 审阅范围：`/app/core/companion_harness/` 源码与 `/app/core/companion_harness/AGENTS.md`、`/app/core/companion_harness/companion/AGENTS.md`。
- 上文「术语」「相对设计目标仍缺或明显偏薄」已覆盖主要结论；细节以代码与 AGENTS 为准。

## 下一步任务目标

- 在 `/app/core/companion_harness/companion/AGENTS.md` 或上层与 iMate 相关的架构文档中，写入上述术语约定并固定中英文对照。
- 定义 **伴侣用户模型** 的数据边界：字段集合、更新来源（用户显式 / 隐式信号如 `/app/schemas/implicit_signals.py`、记忆抽取等）、与 `USER.md`、transcript、记忆流水线的读写关系。
- 若新增持久化或 Pydantic schema：与 `companion_memory_document_versions`、`ContextMeta`（`/app/core/companion_harness/companion/models.py`）等现有真源对齐，命名与注释中统一使用「伴侣用户模型」以防与 ORM User 混淆。
- 按产品优先级推进 Companion Harness 缺口：多媒介通道抽象；用户侧多模态输入契约；独立于用户每轮输入的「世界/环境」状态与事件（若仍纳入本里程碑）。
- 实现或跟进 **companion-dual-envelope-reasoning-channel**：工具后台完成轮次从 `reasoning` / `reasoning_details` 与 `content` 统一解析双通道 envelope，与 `/app/core/companion_harness/companion/tool_bg_routing.py` 行为一致。
- 为「无输出 LLM 调用」补充复现与降级策略（含观测字段与用户可见行为），关闭或降级为可监控的已知限制。
- 为 `/app/core/companion_harness/__init__.py` 补充包级 docstring，说明本包在系统中的角色（仅 docstring，不放功能性代码）。
- 评估是否将本计划中的「伴侣用户模型」拆成独立 FR 文档（`docs/FR_*.md`）并挂链接至本文档。

## 相关路径

- `/app/core/companion_harness/`
