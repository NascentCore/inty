# INTY v2 核心 Agentic 组件 — 本地文本聊天原型实现计划

> 依据：[INTY_v2_CORE_AGENTIC_COMPONENT_TECH_ARCHITECTURE.md](../INTY_v2_CORE_AGENTIC_COMPONENT_TECH_ARCHITECTURE.md) **§2–§6（核心 text chat）** 与 [INTY_v2_DESIGN.md](../INTY_v2_DESIGN.md) 中三层人格 + 双层记忆的**概念对齐**（实现极简）。  
> 本原型 **不** 实现 HTTP 服务、**不使用任何数据库**、**不** 做错误处理、**不** 追求完备性；**全部状态用本地文件（以 Markdown 为主）持久化**，便于本地测试与手工检查。

---

## 1. 目标与非目标

### 1.1 目标

- 在 **单进程、终端本地** 跑通：**从 Markdown 读入人格与记忆 → 读用户一行文本 → 按固定顺序拼 system → 调 LLM → 打印助手回复 → 把本轮写入文件（对话日志 + 可选记忆更新）**。
- **持久化一律走文件系统**（默认一个 **workspace 目录**，例如 `experimental/inty_v2_text_chat_prototype/workspace/` 或由 CLI `--workspace` 指定）：
  - **人格与约定**：`IDENTITY.md`、`SOUL.md`、`USER.md`（用户称呼、界限、密度等纯文本即可）。
  - **长期记忆定稿**：`MEMORY.md`（短列表或段落，供拼进 system；可随对话**更新**）。
  - **日记层（可选但推荐）**：`memory/YYYY-MM-DD.md` 每文件追加当日轮次摘要一行，与 [产品定位.md](../产品定位.md) 叙事一致；提炼进 `MEMORY.md` 的规则可极简（见 §3.3）。
  - **会话消息**：`transcript.jsonl` 每行一条 JSON（`role`, `content`, `ts`），重启 REPL 可续聊；或简化为仅内存 + 只持久化日记，二选一在 README 写死。
- 用 **Pydantic** 描述内存中的结构体（加载自文件后的对象）；写回时用字符串拼接或模板即可，**不必**上 front matter 解析库。
- 用 **Cyclopts** + 显式 **`main.py`** 作为入口（与仓库 [AGENTS.md](../../AGENTS.md) 约定一致），例如：`python -m experimental.inty_v2_text_chat_prototype.main repl --workspace ./workspace`。

### 1.2 非目标（刻意不做）

| 项 | 说明 |
|----|------|
| HTTP / FastAPI / Uvicorn | 不做任何 Web 服务 |
| **PostgreSQL / SQLAlchemy / Alembic / 任何数据库** | **原型完全不使用数据库**；与生产路径分离 |
| 鉴权、限流、幂等 `event_id` | 不实现 |
| try/except、重试、超时、友好报错 | **不做错误处理**；缺文件、坏 JSON、API 失败时允许直接抛栈 |
| 流式输出 | 可 **非流式** 一次返回全文 |
| pgvector、异步 job 队列、push、自治心跳 | 不实现 |
| Android / `app/schemas` 同步 | 原型不暴露 HTTP JSON 合同 |

---

## 2. 放置位置与目录结构（建议）

在 **`experimental/`** 下新建独立包：

```text
experimental/inty_v2_text_chat_prototype/
  main.py             # Cyclopts：repl / once / init-workspace
  models.py           # Pydantic：ChatMessage, WorkspaceState, ...
  paths.py            # workspace 下各文件路径常量
  file_store.py       # read_text / append_text / write_text（薄封装，无错误处理）
  prompts.py          # build_system_prompt：按架构 §10.2 顺序拼接（从 state 取字符串）
  orchestrator.py     # run_turn：读文件 → LLM → 写 transcript → 可选记忆更新
  memory_update.py    # 可选：第二轮 LLM 或规则，更新 MEMORY.md / 追记日记
  client.py           # 单次 chat.completions
  workspace/          # 可提交 .gitkeep + 示例 *.md；或 init-workspace 生成模板
    IDENTITY.md
    SOUL.md
    USER.md
    MEMORY.md
    memory/
    transcript.jsonl
  README.md
```

**原则**：不修改 `app/`；**仅文件 I/O**，无 DB。

---

## 3. 核心逻辑

### 3.1 启动 / 加载

1. 解析 `--workspace`（默认相对包目录 `workspace/`）。
2. 读取 `IDENTITY.md`、`SOUL.md`、`USER.md`、`MEMORY.md`（缺失则视为空字符串或要求 `init` 已运行）。
3. 读取 `transcript.jsonl` 载入最近 N 条为 `transcript`（无文件则空列表）。

### 3.2 每一轮对话

1. `system = build_system_prompt(identity, soul, user_md, memory_md, context_mode)`，顺序与架构 **§10.2** 前段一致（text chat：无工具、无多模态 schema）。
2. `messages = [{"role":"system","content": system}] + transcript + [{"role":"user","content": text}]`。
3. `assistant_text = complete(messages)`。
4. 追加两行到 `transcript.jsonl`（user / assistant）；更新内存中的 `transcript` 并做窗口截断。
5. **记忆更新（原型必备能力，仍无 DB）**：见 §3.3。

### 3.3 记忆更新（本地文件，极简）

任选一种或两种都做（实现计划里写死一种即可，避免范围膨胀）：

| 策略 | 行为 | 复杂度 |
|------|------|--------|
| **A. 仅日记** | 在 `memory/YYYY-MM-DD.md` 末尾追加一行：`[时间] 用户: … / 助手: …`（可截断长度） | 最低；`MEMORY.md` 靠人工编辑 |
| **B. 日记 + 定稿** | 每轮或每 K 轮后，**第二次**调用 LLM：输入「本轮摘要 + 当前 `MEMORY.md`」，输出**整份**新的 `MEMORY.md` 正文（短，如 ≤ 2k 字），**覆盖写文件** | 模拟生产「提炼」；仍无向量 |
| **C. 追加定稿** | 模型只输出若干条 bullet，直接 `append` 到 `MEMORY.md` | 实现快，易重复，仅适合演示 |

推荐原型：**A + B**（日记可审计，定稿可测试「记忆是否进下一轮 system」）。

**不做**：向量检索、冲突合并策略、并发锁；单用户单文件假设。

---

## 4. 依赖与配置

- **Python** + 仓库根 **venv**；**Pydantic**、**openai**、**cyclopts**、**python-dotenv**。
- 调用方式同 [experimental/agentic_ai_companion](../../experimental/agentic_ai_companion/) 或最小 `openai.OpenAI`。
- **环境变量**：`OPENROUTER_API_KEY` / `OPENAI_API_KEY`、`INTY_V2_PROTO_MODEL`；记忆更新若用第二模型可共用或单独 env（可选）。

---

## 5. CLI 行为（Cyclopts）

- `init-workspace --path ...`：写入上述空模板 `IDENTITY.md` / `SOUL.md` / `USER.md` / `MEMORY.md` / `memory/.gitkeep`。
- `repl --workspace ...`：循环输入直到 `quit` / EOF。
- `once --workspace ... --message "..."`：单轮。
- **不做**：参数校验与帮助润色。

---

## 6. 实现顺序（建议任务清单）

1. `paths.py` + `file_store.py` + `init-workspace` 模板内容。
2. `models.py`：`ChatMessage`、加载后的 `PromptBundle`（四段 markdown 字符串）。
3. `prompts.py`：`build_system_prompt(...)`。
4. `client.py`：`complete(...)`。
5. `orchestrator.py`：`run_turn` 含读 transcript、写 jsonl。
6. `memory_update.py`：策略 A；再策略 B（第二次 LLM）。
7. `main.py` 串联。
8. `README.md`：workspace 结构说明、如何测「改 MEMORY 后重启是否记住」。

---

## 7. 完成标准（自测）

- 删除进程后再次启动 `repl`，**transcript.jsonl** 使对话可续（若采用该策略）。
- 编辑 `MEMORY.md` 或通过 **B** 自动生成后，下一轮 **system** 中能体现新记忆（可用 `--debug-print-system` 一类开关看一眼，提交前可选）。
- **全程无数据库连接**（无 `sqlalchemy`、`psycopg` import）。

---

## 8. 与正式架构的衔接（后续 PR，非本原型范围）

| 原型中 | 正式实现（见架构文档） |
|--------|------------------------|
| `*.md` + `transcript.jsonl` | `agents` / `chat_history` / `memory_items` + SQLAlchemy + Alembic |
| 第二次 LLM 覆盖 `MEMORY.md` | 异步 job + `memory_items` 行级更新与向量检索 |
| `run_turn` | FastAPI + `TextTurnInput` |
| 文件 workspace | 按用户 ID 分租户存储或对象存储（非本阶段） |

---

## 9. 文档维护

- 若架构文档 **§2–§7** 变更，同步检查 **§3、§8**。
- 若 [INTY_v2_DESIGN.md](../INTY_v2_DESIGN.md) 对记忆/人格分层有调整，同步 **§1.1、§2** 文件名与语义。
