# INTY v2 核心 Agentic 组件 — 本地文本聊天原型实现计划

> 依据：[INTY_v2_CORE_AGENTIC_COMPONENT_TECH_ARCHITECTURE.md](../INTY_v2_CORE_AGENTIC_COMPONENT_TECH_ARCHITECTURE.md) **§2–§7（核心 text chat）** 的逻辑与 **§3「Companion Control Plane + Text Turn Orchestrator」** 的分层思想；提示词顺序对齐 **§10.2**（text chat 子集见 §4.2）。  
> **§20（参考架构 / 外部门户）** 中的工程约束在本原型中仅做 **最小可对齐**：单一助手写入路径、编排分层、工作区级「控制面上下文」；**不**实现 HTTP、幂等、Worker 或多入口。  
> 与 [INTY_v2_DESIGN.md](../INTY_v2_DESIGN.md) 中三层人格 + 双层记忆的**概念对齐**（实现极简）。  
> 本原型 **不** 实现 HTTP 服务、**不使用任何数据库**、**不** 做错误处理、**不** 追求完备性；**全部状态用本地文件（以 Markdown 为主）持久化**，便于本地测试与手工检查。

---

## 1. 目标与非目标

### 1.1 目标

- 在 **单进程、终端本地** 跑通：**从 Markdown 读入人格与记忆 → 读用户一行文本 → 按固定顺序拼 system → 调 LLM → 打印助手回复 → 把本轮写入文件（对话日志 + 可选记忆更新）**。
- **持久化一律走文件系统**（默认一个 **workspace 目录**，例如 `experimental/inty_v2_text_chat_prototype/workspace/` 或由 CLI `--workspace` 指定）：
  - **人格与约定**：`IDENTITY.md`、`SOUL.md`、`USER.md`（用户称呼、界限、密度等纯文本即可）。
  - **长期记忆定稿**：`MEMORY.md`（短列表或段落，供拼进 system；可随对话**更新**）。
  - **日记层（可选但推荐）**：`memory/YYYY-MM-DD.md` 每文件追加当日轮次摘要一行，与 [产品定位.md](../产品定位.md) 叙事一致；提炼进 `MEMORY.md` 的规则可极简（见 §4.3）。
  - **会话消息**：**必须**使用 `transcript.jsonl`（每行一条 JSON：`role`, `content`, `ts`），用于持久化轮次；**不得**采用「仅内存、不落 transcript」模式，以满足 §8 续聊验收。
  - **控制面上下文（建议）**：`context.json`（可选小文件）固定本 workspace 对应的 **`context_mode`**、以及原型用的 **`user_id` / `companion_id` / `chat_id` 占位字符串**（与架构 §4、§20.2 字段对齐，便于将来对接 REST；无则代码内默认 `intimate` + 占位 ID）。
- 用 **Pydantic** 描述内存中的结构体（加载自文件后的对象）；写回时用字符串拼接或模板即可，**不必**上 front matter 解析库。
- 用 **Cyclopts** + 显式 **`main.py`** 作为入口（与仓库 [AGENTS.md](../../AGENTS.md) 约定一致），例如：`python -m experimental.inty_v2_text_chat_prototype.main repl --workspace ./workspace`。

### 1.2 非目标（刻意不做）

| 项 | 说明 |
|----|------|
| HTTP / FastAPI / Uvicorn | 不做任何 Web 服务 |
| **PostgreSQL / SQLAlchemy / Alembic / 任何数据库** | **原型完全不使用数据库**；与生产路径分离 |
| 鉴权、限流、幂等 `event_id` | 不实现（架构 §4.1 / §20.3 在正式版中补） |
| try/except、重试、超时、友好报错 | **不做错误处理**；缺文件、坏 JSON、API 失败时允许直接抛栈 |
| 流式输出 | 可 **非流式** 一次返回全文 |
| pgvector、异步 job 队列、push、自治心跳 | 不实现 |
| Android / `app/schemas` 同步 | 原型不暴露 HTTP JSON 合同 |
| 多入口并发（HTTP + Worker） | 单线程 REPL；**不**验证 §20.3 的 per-chat 串行 |

---

## 2. 与正式架构的组件对照（含 §20）

下列映射保证原型在**命名与职责**上与 [架构文档 §3–§6、§20](../INTY_v2_CORE_AGENTIC_COMPONENT_TECH_ARCHITECTURE.md) 一致，便于后续替换为 FastAPI + ORM。

| 架构文档中的组件 | 原型中的落点 | 说明 |
|-------------------|--------------|------|
| **Companion Control Plane**（归一化入参、解析 `chat_id` / `agent_id`） | `context.json` 读取 + `paths.py` 解析 `--workspace`；单 REPL 即「单会话」 | 无 HTTP；用文件表达「已绑定到本 workspace 的会话与模式」 |
| **Text Turn Orchestrator**（写用户 → 拉历史 → 拼 prompt → LLM → 写助手） | **`orchestrator.py` 的 `run_turn`** 为 **唯一** 写入助手回复到 `transcript.jsonl` 的入口 | 与 §3、§6、**§20.1**「助手侧只经一条业务路径落库」同构；禁止在 `memory_update` 或其它模块直接写「本轮助手发言」到 transcript |
| 内层「单次 LLM 调用」 | `client.py` 的 `complete(...)` | 与 **§20.4**「外层编排 vs 内层模型」一致；不在 `client` 内拼业务 system（由 `prompts.py` 产出） |
| 提示词装配（§10.2 顺序，text chat 子集） | `prompts.py` 的 `build_system_prompt(...)` | §4.2：无工具列表、无多模态 schema |
| 记忆异步演进（正式版） | `memory_update.py`（同步、第二路 LLM 可选） | **仅允许**由 `orchestrator.run_turn` **在助手落库之后**调用；对应正式版「扩展不阻塞主路径」的精神（§6 第 9 步、§11） |
| 非 HTTP 路径携带控制面上下文（§20.2） | 本原型仅 REPL；若日后加 `scripts/scheduled_fake_turn.py`，须 **同样** 读同一 `context.json` 并 **只调** `run_turn` | 文档约束，可不写脚本 |

### 2.1 原型最小分层图（与架构 §3 对应）

```
用户输入（stdin）
        │
        ▼
┌───────────────────────────────────────┐
│  Control Plane（进程内，极简）          │
│  workspace + context.json → 单会话语义  │
└───────────────────┬───────────────────┘
                    ▼
┌───────────────────────────────────────┐
│  Text Turn Orchestrator               │
│  orchestrator.run_turn                │
│  读 transcript → prompts → client →    │
│  写 user/assistant 行 → memory_update  │
└───────────────────┬───────────────────┘
                    ▼
┌───────────────────────────────────────┐
│  本地文件（*.md, transcript.jsonl）     │
└───────────────────────────────────────┘
```

---

## 3. 放置位置与目录结构（建议）

在 **`experimental/`** 下新建独立包：

```text
experimental/inty_v2_text_chat_prototype/
  main.py             # Cyclopts：repl / once / init-workspace
  models.py           # Pydantic：ChatMessage, WorkspaceState, ContextMeta, ...
  paths.py            # workspace 下各文件路径常量
  file_store.py       # read_text / append_text / write_text（薄封装，无错误处理）
  prompts.py          # build_system_prompt：按架构 §10.2 顺序拼接（从 state 取字符串）
  orchestrator.py     # run_turn：唯一入口；读文件 → LLM → 写 transcript → 可选记忆更新
  memory_update.py    # 可选：第二轮 LLM 或规则，更新 MEMORY.md / 追记日记（仅由 orchestrator 调用）
  client.py           # 单次 chat.completions（内层）
  workspace/          # 可提交 .gitkeep + 示例 *.md；或 init-workspace 生成模板
    IDENTITY.md
    SOUL.md
    USER.md
    MEMORY.md
    memory/
    transcript.jsonl
    context.json      # 可选：context_mode, user_id, companion_id, chat_id（占位）
  README.md
```

**原则**：不修改 `app/`；**仅文件 I/O**，无 DB。**助手可见文本**只经 `orchestrator.run_turn` 写入 transcript（§20.1）。

---

## 4. 核心逻辑

### 4.1 启动 / 加载

1. 解析 `--workspace`（默认相对包目录 `workspace/`）。
2. **必选文件校验**（`repl` / `once` 在加载前执行）：下列路径 **必须存在**（由 `init-workspace` 生成；内容可为空模板或 `transcript.jsonl` 零行），**任一缺失则立即报错退出**，不兜底为空字符串：  
   `IDENTITY.md`、`SOUL.md`、`USER.md`、`MEMORY.md`、`transcript.jsonl`。
3. 读取上述文件内容；`transcript.jsonl` 无有效行则 `transcript` 为空列表。
4. 读取 `context.json`（若存在）得到 `context_mode` 与占位 ID；否则默认 `context_mode=intimate`，ID 为原型常量。

### 4.2 每一轮对话（须经 `run_turn`）

1. `system = build_system_prompt(identity, soul, user_md, memory_md, context_mode)`，顺序与架构 **§10.2** 前段一致（text chat：无工具、无多模态 schema）。
2. `messages = [{"role":"system","content": system}] + transcript + [{"role":"user","content": text}]`。
3. `assistant_text = complete(messages)`（**仅** `client.py`）。
4. 追加两行到 `transcript.jsonl`（user / assistant）；更新内存中的 `transcript` 并做窗口截断。
5. **记忆更新（原型必备能力，仍无 DB）**：见 §4.3；**仅**在步骤 4 完成后由 orchestrator 调用 `memory_update`。

### 4.3 记忆更新（本地文件，极简）

任选一种或两种都做（实现计划里写死一种即可，避免范围膨胀）：

| 策略 | 行为 | 复杂度 |
|------|------|--------|
| **A. 仅日记** | 在 `memory/YYYY-MM-DD.md` 末尾追加一行：`[时间] 用户: … / 助手: …`（可截断长度） | 最低；`MEMORY.md` 靠人工编辑 |
| **B. 日记 + 定稿** | 每轮或每 K 轮后，**第二次**调用 LLM：输入「本轮摘要 + 当前 `MEMORY.md`」，输出**整份**新的 `MEMORY.md` 正文（短，如 ≤ 2k 字），**覆盖写文件** | 模拟生产「提炼」；仍无向量 |
| **C. 追加定稿** | 模型只输出若干条 bullet，直接 `append` 到 `MEMORY.md` | 实现快，易重复，仅适合演示 |

推荐原型：**A + B**（日记可审计，定稿可测试「记忆是否进下一轮 system」）。

**不做**：向量检索、冲突合并策略、并发锁；单用户单文件假设。

---

## 5. 依赖与配置

- **Python** + 仓库根 **venv**；**Pydantic**、**openai**、**cyclopts**、**python-dotenv**。
- 调用方式同 [experimental/agentic_ai_companion](../../experimental/agentic_ai_companion/) 或最小 `openai.OpenAI`。
- **环境变量**：`OPENROUTER_API_KEY`（原型 `client` 固定 OpenRouter base URL，仅认此变量）、`INTY_V2_PROTO_MODEL`；记忆更新若用第二模型可共用或单独 env（可选）。

---

## 6. CLI 行为（Cyclopts）

- `init-workspace --path ...`：写入上述空模板 `IDENTITY.md` / `SOUL.md` / `USER.md` / `MEMORY.md`、**空文件 `transcript.jsonl`**（零行即可）、`memory/.gitkeep`，以及可选 **`context.json` 模板**（含默认 `context_mode` 与占位 ID）。
- `repl --workspace ...`：循环输入直到 `quit` / EOF。
- `once --workspace ... --message "..."`：单轮。
- **不做**：参数校验与帮助润色。

---

## 7. 实现顺序（建议任务清单）

1. `paths.py` + `file_store.py` + `init-workspace` 模板内容（含必选 `transcript.jsonl` 与 `context.json` 可选）。
2. `models.py`：`ChatMessage`、加载后的 `PromptBundle`（IDENTITY/SOUL/USER/MEMORY、可选 AGENTS/TOOLS/HEARTBEAT、当日 `memory_raw_diary_today_md` / `memory_day_summary_today_md`）、`ContextMeta`。
3. `prompts.py`：`build_system_prompt(...)`。
4. `client.py`：`complete(...)`。
5. `orchestrator.py`：`run_turn` 含读 transcript、写 jsonl；**保证**助手行只经此函数写入。
6. `memory_update.py`：`memory/daily/` 原始流水追加 → 当日总结（`memory/YYYY-MM-DD.md`）→ `MEMORY.md` 策展；**仅 orchestrator 调用**。
7. `main.py` 串联。
8. `README.md`：workspace 结构说明、与架构 §3/§20 的对照一句、如何测「改 MEMORY 后重启是否记住」。

---

## 8. 完成标准（自测）

- 删除进程后再次启动 `repl`，依赖 **`transcript.jsonl`** 持久化的历史使对话可续（必选路径；与 §4.1 必选文件一致）。
- 编辑 `MEMORY.md` 或通过 **B** 自动生成后，下一轮 **system** 中能体现新记忆（可用 `--debug-print-system` 一类开关看一眼，提交前可选）。
- **全程无数据库连接**（无 `sqlalchemy`、`psycopg` import）。
- 代码审查：**无**在 `orchestrator` 外写入「本轮 assistant 回复」到 `transcript.jsonl` 的路径。

---

## 9. 与正式架构的衔接（后续 PR，非本原型范围）

| 原型中 | 正式实现（见架构文档） |
|--------|------------------------|
| `*.md` + `transcript.jsonl` | `agents` / `chat_history` / `memory_items` + SQLAlchemy + Alembic |
| `context.json` 占位 | `user_id` / `chat_id` / `context_mode` 与 `CanonicalTurnEvent`（§10.1） |
| 第二次 LLM 覆盖 `MEMORY.md` | 异步 job + `memory_items` 行级更新与向量检索 |
| `run_turn` | FastAPI + `TextTurnInput` |
| 单一 `run_turn` 写助手消息 | **§20.1** `append_assistant_message` 唯一路径 |
| 文件 workspace | 按用户 ID 分租户存储或对象存储（非本阶段） |
| Orchestrator / client 分层 | **§20.4** 外层事务与内层 LLM 分离 |

---

## 10. 文档维护

- 若架构文档 **§2–§7** 或 **§20** 变更，同步检查 **§2、§4、§9、§10**。
- 若 [INTY_v2_DESIGN.md](../INTY_v2_DESIGN.md) 对记忆/人格分层有调整，同步 **§1.1、§3** 文件名与语义。
- 扩展章节（架构 **§8–§20**）落地时，**优先**保持「Orchestrator 唯一写助手消息」与 **§20.2** 上下文传递，再扩 HTTP/Worker。
