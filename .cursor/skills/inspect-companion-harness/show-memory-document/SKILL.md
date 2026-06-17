---
name: inspect-companion-harness-show-memory-document
description: >-
  Print a companion MemoryStore document (e.g. STYLE.md, IDENTITY.md) from Postgres
  companion_memory_document_versions. Uses .cursor/skills/scripts/companion_memory_show_document.py.
  Parent: ../SKILL.md.
---

# Companion：打印指定 MemoryStore 文档

**父技能**：`../SKILL.md`（`inspect-companion-harness`）。

## 何时使用

- 核对 `STYLE.md` / `SOUL.md` / `MEMORY.md` 等是否落库、正文是否与 REPL/LangSmith 一致。
- 对比同一文档的多个 `sequence_id`（append-only 版本）。
- 需要 **全 agent 文档总览** 时，用 [`list-agent-documents/SKILL.md`](../list-agent-documents/SKILL.md)。

## 脚本（读库唯一入口）

仓库根执行（`PYTHONPATH=.`）：

```bash
PYTHONPATH=. python .cursor/skills/scripts/companion_memory_show_document.py STYLE.md \
  --companion-id <agent_id>
```

**仅有 `agent_id`、且该 companion 只有一个 `(user_id, chat_id)` 时**可省略 scope；否则脚本会列出候选 scope 并退出，需补 `--user-id` / `--chat-id`。

### 常用参数

| 参数 | 作用 |
|------|------|
| `DOCUMENT`（位置参数） | 逻辑路径：`STYLE.md`、`context.json`、`memory/daily/2026-05-18.md` 等 |
| `--companion-id` | WebSocket/API 的 `agent_id` |
| `--user-id` / `--chat-id` | MemoryStore 作用域三元组 |
| `--config` | 默认 `config.yaml`；CI 可用 `devops/config.yaml.test` |
| `--limit N` | 打印最近 N 个版本（默认 1） |
| `--meta-only` | 只打 `sequence_id` / `created_at` / 字数，不打正文 |
| `--list-scopes` | 列出该 companion 下所有 `(user_id, chat_id)` |
| `--list-kinds` | 列出该 scope 下各 `document_kind` 的最新 `sequence_id` |

### 示例

```bash
# 最新 STYLE.md 全文
PYTHONPATH=. python .cursor/skills/scripts/companion_memory_show_document.py STYLE.md \
  --companion-id 4ca541f4-64fa-43c0-af6c-7f440def4839

# 本地测试用户 + 明确 chat
PYTHONPATH=. python .cursor/skills/scripts/companion_memory_show_document.py STYLE.md \
  --companion-id <agent_id> \
  --user-id user-testing \
  --chat-id <chat_id>

# 最近两版对比
PYTHONPATH=. python .cursor/skills/scripts/companion_memory_show_document.py STYLE.md \
  --companion-id <agent_id> --limit 2

# 该会话写过哪些 document_kind
PYTHONPATH=. python .cursor/skills/scripts/companion_memory_show_document.py STYLE.md \
  --companion-id <agent_id> --list-kinds
```

## 路径 ↔ `document_kind`

由 `app/core/companion_harness/memory/memory_store_document_mapping.py` 解析；脚本与 ORM 共用 `parse_memory_store_relative_path`。

## 注意

- REPL 的 `user_msg_uuid` / `langsmith_trace_id` **不是** `chat_id`。
- 大字段（`transcript.jsonl` 等）先用 `--meta-only` 或 `--list-kinds`，避免终端刷屏。
