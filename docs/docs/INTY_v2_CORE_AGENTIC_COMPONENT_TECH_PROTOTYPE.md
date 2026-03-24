# INTY v2 核心 Agentic 组件 — 本地文本聊天原型实现计划

> 依据：[INTY_v2_CORE_AGENTIC_COMPONENT_TECH_ARCHITECTURE.md](../INTY_v2_CORE_AGENTIC_COMPONENT_TECH_ARCHITECTURE.md) **§2–§6（核心 text chat）**。  
> 本原型 **不** 实现 HTTP 服务、**不** 做错误处理、**不** 追求完备性；仅验证 **提示词分层装配 + 一轮编排 + 多轮内存中的对话** 是否跑通。

---

## 1. 目标与非目标

### 1.1 目标

- 在 **单进程、终端本地** 跑通：**读用户一行文本 → 按固定顺序拼 system/user 消息 → 调 LLM → 打印助手回复 → 把双方消息留在内存列表里** 供下一轮使用。
- 用 **Pydantic** 描述「一轮输入」和可选的「伴侣静态配置」（对应架构里的 IDENTITY/SOUL 占位，可先写成两三个字符串字段）。
- 用 **Cyclopts** + 显式 **`main.py`** 作为入口（与仓库 [AGENTS.md](../../AGENTS.md) 约定一致），例如：`python -m experimental.inty_v2_text_chat_prototype.main` 或等价路径。

### 1.2 非目标（刻意不做）

| 项 | 说明 |
|----|------|
| HTTP / FastAPI / Uvicorn | 不做任何 Web 服务；与架构文档生产路径分离 |
| PostgreSQL / SQLAlchemy / Alembic | 不做持久化；会话 = 进程内 `list[Message]` |
| 鉴权、限流、幂等 `event_id` | 不实现 |
| try/except、重试、超时、友好报错 | **不做错误处理**；配置缺失或 API 失败时允许进程直接抛栈 |
| 流式输出 | 原型可 **非流式** 一次返回全文，降低胶水代码（架构中的流式留待接入 FastAPI 时再做） |
| 记忆抽取、向量、异步 job、自治心跳 | 不属于本原型 |
| Android / `app/schemas` 同步 | 原型不暴露 HTTP JSON 合同 |

---

## 2. 放置位置与目录结构（建议）

在 **`experimental/`** 下新建独立包（名称可调整，示例）：

```text
experimental/inty_v2_text_chat_prototype/
  main.py           # Cyclopts CLI：repl / 单条 --message
  models.py         # Pydantic：TextTurnInput, CompanionProfile, ChatMessage
  prompts.py        # build_system_prompt(...)：按架构 §10.2 顺序拼接文本块（极简版）
  orchestrator.py   # run_turn(...)：append user → call LLM → append assistant
  client.py         # 单次 chat.completions（或仓库现有 OpenAI 兼容封装的最薄包装）
  requirements.txt  # 可选：仅当与根 requirements 冲突时列出；否则依赖仓库根 venv
  README.md         # 一行：如何设 API Key、如何运行
```

**原则**：不修改 `app/` 生产代码路径；原型自洽，便于删除或整体迁移。

---

## 3. 核心逻辑（最简流水线）

与架构文档 **§6** 对应，但去掉 DB 与流式：

1. 初始化空列表 `transcript: list[ChatMessage]`（role + content 字符串即可）。
2. 用户输入 `text`（REPL `input()` 或 CLI 参数）。
3. `system = build_system_prompt(companion, user_notes)`  
   - **极简落地**：用 4～5 个字符串块顺序拼接即可，不必单独文件：  
     `base_safety` → `identity` → `soul` → `context_mode 一句话` → `user_agreement 一句话` → `history_instruction`。  
   - **不做** 长期记忆检索块（留空或固定占位句）。
4. `messages = [{"role":"system","content": system}] + transcript + [{"role":"user","content": text}]`。
5. 调用 LLM，得到 `assistant_text`。
6. `transcript.append(user_msg); transcript.append(assistant_msg)`。
7. 打印 `assistant_text`。

**历史窗口**：对 `transcript` 做简单截断（例如只保留最近 N 条 message 对象），避免 token 爆；N 写死在代码常量即可。

---

## 4. 依赖与配置

- **Python**：与仓库一致（如 3.12），使用仓库根目录 **venv**。
- **库**：优先复用根 `requirements.txt` 已有 **Pydantic**、**openai**、**cyclopts**、**python-dotenv**；不在原型里重复造 HTTP 客户端（`app/` 生产代码有 HTTP 约束；本原型在 `experimental/` 内可用与 [experimental/agentic_ai_companion](../../experimental/agentic_ai_companion/) 相同的 OpenRouter/OpenAI 调用方式，或最小 `openai.OpenAI`）。
- **环境变量**：`.env` 或 export，例如 `OPENROUTER_API_KEY` / `OPENAI_API_KEY`、可选 `INTY_V2_PROTO_MODEL`（默认一个便宜聊天模型即可）。

---

## 5. CLI 行为（Cyclopts）

- **默认子命令**：`repl` — 循环 `input("You: ")`，直到 EOF 或 `quit`。
- **可选**：`once --message "..."` — 跑一轮后退出（便于脚本冒烟）。
- **不做**：子命令帮助文案的完美性、非法参数校验。

---

## 6. 实现顺序（建议任务清单）

1. `models.py`：`ChatMessage`、`CompanionProfile`（字段：`identity_text`, `soul_text`, `context_mode` 默认 `intimate`）。
2. `prompts.py`：`build_system_prompt(profile, user_agreement: str | None) -> str`。
3. `client.py`：`complete(messages: list[dict]) -> str`（单函数）。
4. `orchestrator.py`：`run_turn(transcript, profile, user_text) -> tuple[新 transcript, assistant_text]`。
5. `main.py`：Cyclopts 注册 `repl` / `once`，`load_dotenv()`，构造全局 `transcript` 与 `profile`（可从常量或 CLI 可选参数读入）。
6. `README.md`：三行命令跑起来。

---

## 7. 完成标准（自测）

- 本地执行入口命令后，能连续多轮对话，且 **system 提示中可见** IDENTITY/SOUL 顺序（可在第一轮暂时 `print(system)` 调试，提交前删除或加 `--debug` 开关；若加开关，仍属「极简」，不做完整 logging）。
- 无需单元测试门禁（与「原型」定位一致）；若后续要加，最多一个 `pytest` 测 `build_system_prompt` 子串顺序。

---

## 8. 与正式架构的衔接（后续 PR，非本原型范围）

| 原型中 | 正式实现（见架构文档） |
|--------|------------------------|
| 内存 `transcript` | `chat_history` + SQLAlchemy |
| `run_turn` | FastAPI endpoint + TextTurnInput |
| `complete` 非流式 | 流式 SSE + 落库助手消息 |
| 常量 `CompanionProfile` | `agents` 表 + AgentManager 装配 |

---

## 9. 文档维护

- 若架构文档 **§2–§7** 对「核心 text chat」有变更，同步检查本节 **§3、§8** 是否仍对齐。
