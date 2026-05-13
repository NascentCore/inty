# Design

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

## 4.5 配置管理：python-dotenv (repl) + config-files

用途：

- 本地/实验环境使用 dotenv 加载密钥。
- 服务级配置通过 config.yaml+[config.py](/app/utils/config.py)。

原则：

- 配置读取集中在 `config.yaml`，业务代码不直接 `os.environ[...]`。
- 缺失关键配置时启动即失败（fail fast）。

## 4.6 持久化

- PostgreSQL + SQLAlchemy（生产化、并发与查询能力）。
- 迁移：Alembic 管理 schema 版本。

## 4.7 渠道与外部服务

- Telegram：复用现有 long polling 与 sendMessage 逻辑。
- SMS：通过 Twilio SMS API（adapter 封装）。
- 电话：复用现有 Twilio 外呼 + TwiML Stream（作为 action 能力）。

## 4.8 可观测性与日志

- REPL: metadata (for debugging) & content messages
- 标准库 logging（结构化 key-value 风格）。
- 指标维度：inbound latency、LLM latency、dispatch latency、retry count、drop count。
- 错误分级：transient vs terminal。
