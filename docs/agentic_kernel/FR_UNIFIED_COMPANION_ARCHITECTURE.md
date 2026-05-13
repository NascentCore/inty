# FR_UNIFIED_COMPANION_ARCHITECTURE

## 1. 文档目的与执行定位

本文档定义“统一个人伴侣系统（Unified Companion System）”的高层意图、系统架构、代码级技术选型，以及模块与技术的对应关系。  
该文档是后续实现与评审的执行依据（source of truth）。

执行约束：

- 先稳定性后智能化：先完成可靠性与幂等，再扩展高级记忆/规划能力。
- 单一核心循环：所有渠道共享同一个 Orchestrator 与 Memory/Plan Core。
- 失败尽早暴露：不做吞错式防御编程。

## 2. 高层业务意图（High-level Intent）

目标能力：

1. 统一渠道沟通：Telegram / SMS / 电话（电话第一阶段作为 outbound call action）。
2. 人类式记忆：从聊天中持续提取并更新用户偏好、关系边界、事件与目标。
3. 持续计划：基于记忆自动生成后续关怀动作，并按规则执行与回写。
4. 长期连续性：跨会话保留状态，避免“每轮重置”的短期机器人行为。

非目标（本阶段）：

- 不在第一阶段实现完整电话双向会话栈（来电接入、转写、会话状态机）。
- 不在第一阶段引入复杂多代理协作或多租户分片调度。

## 3. 系统总体架构（Logical Architecture）

## 3.1 分层架构

1. Channel Gateway（渠道网关）
2. Conversation Orchestrator（统一会话编排）
3. Memory Core（记忆核心）
4. Continuous Planner（持续规划）
5. Execution & Safety（执行与安全策略）
6. Persistence & Observability（持久化与可观测）

## 3.2 单一核心循环（Runtime Loop）

`Inbound Event -> Identity Resolve -> Memory Extract/Update -> Plan Refresh -> Reply Compose -> Dispatch -> Outcome Persist`

说明：

- Reactive path：由用户入站消息触发。
- Proactive path：由 Scheduler 扫描到期计划动作触发。

## 3.3 进程拓扑（Deployment Topology）

- `companion serve inbound`
  - 单消费者读取 Telegram/SMS 入站。
  - 驱动 reactive loop。
- `companion serve scheduler`
  - 扫描并执行到期计划动作。
- `companion admin replay`
  - 事件回放、故障排查、离线分析。

硬约束：

- Telegram bot token 仅允许一个 long-poll consumer。
- 所有出站动作必须幂等可重试（含去重键）。

## 4. 代码层技术选型（Tech Stack Selection）

## 4.1 语言与运行时

- Python 3.12（与仓库环境一致）。

## 4.2 数据建模与契约：Pydantic v2

用途：

- 统一定义跨模块输入/输出契约（event/memory/plan）。
- 做边界校验、类型约束、序列化与反序列化。
- 防止 dataclass + dict 组合导致的字段漂移。

原则：

- Domain DTO 与 Adapter DTO 均使用 Pydantic BaseModel。
- 入站外部 payload 先过校验再进入业务层。

## 4.3 CLI：Cyclopts

用途：

- 实现统一命令入口：`serve inbound` / `serve scheduler` / `admin replay`。
- 替代散落的 argparse 子脚本。

原则：

- 明确 `main.py` 入口，不使用 `__main__.py`。
- 命令参数类型由注解与模型定义，避免隐式字符串参数。

## 4.4 LLM 接入：OpenAI-SDK（OpenAI-compatible）

用途：

- 统一模型调用层（支持 OpenAI 兼容端点，如 OpenRouter）。
- 支持 chat completion + tool calling。

原则：

- 在 `ModelGateway` 统一封装 SDK 调用、超时、重试、用量日志。
- 上层业务不直接调用 SDK 客户端。

## 4.5 配置管理：python-dotenv + pydantic-settings

用途：

- 本地/实验环境使用 dotenv 加载密钥。
- 服务级配置通过 settings model 聚合与校验。

原则：

- 配置读取集中在 `settings.py`，业务代码不直接 `os.environ[...]`。
- 缺失关键配置时启动即失败（fail fast）。

## 4.6 持久化

- Phase 1 MVP：SQLite（快速迭代）。
- Phase 2+：PostgreSQL + SQLAlchemy（生产化、并发与查询能力）。
- 迁移：Alembic 管理 schema 版本。

## 4.7 渠道与外部服务

- Telegram：复用现有 long polling 与 sendMessage 逻辑。
- SMS：通过 Twilio SMS API（adapter 封装）。
- 电话：复用现有 Twilio 外呼 + TwiML Stream（作为 action 能力）。

## 4.8 可观测性与日志

- 标准库 logging（结构化 key-value 风格）。
- 指标维度：inbound latency、LLM latency、dispatch latency、retry count、drop count。
- 错误分级：transient vs terminal。

## 5. 模块与技术映射（Architecture-to-Code Mapping）

| 架构模块 | 代码模块（建议） | 关键技术 | 职责 |
|---|---|---|---|
| Channel Gateway | `core_v2/adapters/*` | urllib/Twilio SDK/Telegram API + Pydantic | 渠道入站标准化与出站发送 |
| Orchestrator | `core_v2/runtime/orchestrator.py` | Cyclopts 命令驱动 + Pydantic DTO | 单一业务编排循环 |
| Identity Resolver | `core_v2/services/identity_resolver.py` | Pydantic + Repo 接口 | 跨渠道统一 user_id |
| Memory Extractor/Updater | `core_v2/services/memory_*` | OpenAI-SDK（可选抽取）+ 规则引擎 + Pydantic | 偏好/关系/事件记忆更新 |
| Planner/Scheduler | `core_v2/services/planner.py` / `scheduler.py` | 规则引擎 + 持久化 + 幂等执行 | 生成并执行持续计划 |
| Model Gateway | `core_v2/services/model_gateway.py` | OpenAI-SDK | 统一模型调用、日志、重试 |
| Safety Policy | `core_v2/services/safety_policy.py` | 规则配置 + Pydantic | quiet hours、频率、渠道约束 |
| Persistence | `core_v2/repositories/*` | SQLAlchemy/SQLite/PostgreSQL/Alembic | 事件/记忆/计划持久化 |
| Observability | `core_v2/observability/*` | logging | 指标日志、诊断事件 |

## 6. 数据模型（Pydantic Contracts）

## 6.1 InteractionEvent

- `event_id: str`（幂等键）
- `user_id: str`
- `channel: Literal["telegram","sms","voice_call"]`
- `direction: Literal["inbound","outbound"]`
- `content: str`
- `timestamp: datetime`
- `channel_message_id: str | None`
- `metadata: dict[str, Any]`

## 6.2 MemoryItem

- `memory_id: str`
- `user_id: str`
- `memory_type: Literal["preference","relational","episodic","goal_plan"]`
- `key: str`
- `value: str`
- `confidence: float`（0~1）
- `evidence_event_ids: list[str]`
- `status: Literal["candidate","active","stale","conflicted"]`
- `first_seen_at: datetime`
- `last_seen_at: datetime`

## 6.3 PlanAction

- `action_id: str`
- `user_id: str`
- `goal: str`
- `scheduled_at: datetime`
- `preferred_channel: Literal["telegram","sms","voice_call"]`
- `message_strategy: str`
- `constraints: dict[str, Any]`
- `status: Literal["pending","done","skipped","failed"]`
- `result_event_id: str | None`

## 7. 可靠性与一致性设计（First-class Concerns）

1. 单消费者锁
   - Telegram long polling 在同一 token 上仅允许一个进程持有消费者锁。
2. 幂等写入
   - `event_id`、`action_id` 唯一约束；重试不产生重复副作用。
3. 重试策略
   - 仅对可恢复错误做有限次指数退避；不可恢复错误立即失败并报警。
4. Cursor 安全
   - 仅在成功处理后推进应用侧 cursor；避免消息丢失。

## 8. 安全与策略（Safety Policy）

- Quiet Hours：默认夜间仅允许低频文本触达。
- 频率限制：每用户每渠道触达上限。
- 渠道优先级：显式用户偏好优先于系统默认。
- 电话升级条件：需满足明确触发条件，不自动高频电话打扰。

## 9. 分阶段实施路线（Execution Milestones）

## M0：稳定性底座（必须先完成）

- 事件持久化 + 幂等
- Telegram 单消费者锁
- 入站/出站重试与错误分类

DoD：

- 在网络抖动与重复投递下，无重复事件、无静默丢失。

## M1：统一双通道（Telegram + SMS）

- 统一 `InteractionEvent` 接口
- 统一 Orchestrator reactive loop

DoD：

- 两通道均可完成“入站->回复->持久化”闭环。

## M2：最小记忆闭环

- 偏好提取：channel/time/tone
- candidate->active->conflicted 状态流转

DoD：

- 对话中重复偏好可提升置信度并影响回复渠道。

## M3：24h 持续计划

- Planner 生成短期 follow-up
- Scheduler 到期执行并回写结果

DoD：

- 系统可在无人输入时按计划主动触达并记录结果。

## M4：电话能力增强（后续）

- 在完成 M0~M3 后，再评估电话双向会话能力接入。

## 10. 测试与验收依据（作为执行标准）

测试策略：

- 以 feature/integration 为主，优先验证端到端行为与运行稳定性。
- 对关键可靠性机制（幂等、锁、重试）做高信号自动化测试。

最低验收用例：

1. Telegram 重复 update 不导致重复记忆写入。
2. 瞬时网络失败后重试成功，cursor 与事件不丢失。
3. 用户明确“短信优先”后，后续主动计划优先 SMS。
4. 到期计划动作仅执行一次（幂等）。

## 11. 与现有代码的兼容迁移策略

迁移原则：

- 先包裹复用，再替换重构。

具体策略：

1. 复用现有 Telegram inbox 与 bot API 作为 `telegram_adapter` 底座。
2. 复用现有 OpenAI-compatible 调用方式，抽到 `ModelGateway`。
3. 复用现有 Twilio 外呼桥接作为 `voice_call` action。
4. 将当前 `argparse` 入口平滑迁移到 Cyclopts CLI。

## 12. 开发约定（后续执行必须遵守）

- 所有新增跨模块数据结构必须先定义 Pydantic 模型。
- 所有入口命令统一走 Cyclopts。
- 任何会产生副作用的执行路径必须具备幂等键。
- 先提交稳定性里程碑（M0），再提交记忆与规划里程碑（M2/M3）。

---

本文件生效后，后续实现以该架构文档为准；若实现过程中发生偏移，必须先更新本文件再改代码。
