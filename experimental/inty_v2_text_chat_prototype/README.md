# INTY v2 本地文本聊天原型

依据仓库文档 `docs/INTY_v2_CORE_AGENTIC_COMPONENT_TECH_PROTOTYPE.md`：单进程 CLI、Markdown + JSONL 文件持久化、**无 HTTP、无数据库**。与 `docs/INTY_v2_CORE_AGENTIC_COMPONENT_TECH_ARCHITECTURE.md` **§3（编排）**、**§20（单一写入路径）** 对齐：助手对用户可见文本仅通过 `orchestrator.run_turn` 追加到 `transcript.jsonl`。

## 依赖

本目录 [requirements.txt](requirements.txt)（`cyclopts`、`openai`、`pydantic`、`python-dotenv`）。建议在 `inty` 仓库根虚拟环境中安装：

```bash
cd /path/to/inty
uv pip install -r experimental/inty_v2_text_chat_prototype/requirements.txt
```

## 运行方式

在 **`inty/` 目录下**执行（保证 `experimental` 包可解析）：

```bash
cd /path/to/inty
export OPENROUTER_API_KEY=...   # 或 OPENAI_API_KEY（直连 OpenAI）
export INTY_V2_PROTO_MODEL=openai/gpt-4o-mini   # 可选；记忆精炼可用 INTY_V2_PROTO_MEMORY_MODEL
# 可选：SOUL.md 策展（默认与 MEMORY 同模型）；关闭自动写 SOUL：INTY_V2_PROTO_SOUL_UPDATE_DISABLED=1

python -m experimental.inty_v2_text_chat_prototype.main init-workspace --path ./experimental/inty_v2_text_chat_prototype/_ws
python -m experimental.inty_v2_text_chat_prototype.main repl --workspace ./experimental/inty_v2_text_chat_prototype/_ws
python -m experimental.inty_v2_text_chat_prototype.main once --message "你好" --workspace ./experimental/inty_v2_text_chat_prototype/_ws
```

- 默认 `--workspace` 为包内 `workspace/`（需先对该路径 `init-workspace`）。
- `--debug-print-system`：打印本轮拼接后的 system prompt（验收「MEMORY 是否进 system」）。

## Workspace 结构

| 路径 | 说明 |
|------|------|
| `IDENTITY.md` / `SOUL.md` / `USER.md` / `MEMORY.md` | 人格与长期记忆定稿；`SOUL.md` 在每轮记忆管线末尾由 LLM 策展同步（边界与价值观），下一轮 system 即加载 |
| `AGENTS.md` / `TOOLS.md` / `HEARTBEAT.md` | 可选；若存在则注入 system prompt（有单文件长度上限） |
| `transcript.jsonl` | 每行 JSON：`role`（user \| assistant）、`content`、`ts` |
| `context.json` | 可选：`context_mode`、`user_id`、`companion_id`、`chat_id` |
| `memory/YYYY-MM-DD.md` | 日记层（每轮追加一行摘要）；**当日**文件若存在还会整段注入（有长度上限） |

## 自测（对应原型 §8）

1. **续聊**：`repl` 中对话若干轮后退出，再次启动同一 `--workspace`，应能依赖 `transcript.jsonl` 接续上下文。
2. **记忆**：编辑 `MEMORY.md` 或依赖每轮后的记忆精炼（LLM 覆盖 `MEMORY.md`，并同步策展 `SOUL.md`）。`run_turn` 在返回前会**同步**跑完该管线，下一轮输入即加载新 `SOUL.md`（代价是每轮多几次 LLM 调用、耗时更长）。`--debug-print-system` 可验收 SOUL/MEMORY 是否进 system。
3. **无 DB**：代码中不 import `sqlalchemy`、`psycopg` 等。
4. **单一写入**：助手消息追加到 `transcript.jsonl` 仅出现在 `orchestrator.py`（`memory_update` 不写 assistant 行）。

## 刻意不实现

无 HTTP、无流式、无 try/except 兜底、无幂等与并发控制（见原型文档）。
