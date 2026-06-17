---
name: inspect-companion-harness-list-agent-documents
description: >-
  Dump or list every companion MemoryStore document (MemDoc) for an agent_id via
  MemoryStore API. Uses .cursor/skills/scripts/companion_memory_list_agent_documents.py.
  Parent: ../SKILL.md.
---

# Companion：列出 agent 的全部 MemoryStore 文档

**父技能**：`../SKILL.md`（`inspect-companion-harness`）。

## 何时使用

- 给定 **`agent_id`**，一次性查看该 companion 在 Postgres 里有哪些 MemDoc、各自最新 `sequence_id` 与字数。
- 调试 bootstrap / dreaming 后核对 **全量落库**，而不逐个 `document_kind` 查 SQL。
- 需要把某 scope 下全部文档导出到目录做 diff。

单文档精读仍用 **`show-memory-document/SKILL.md`**。

## 脚本（读库 + MemoryStore）

仓库根执行（`PYTHONPATH=.`）：

```bash
PYTHONPATH=. python .cursor/skills/scripts/companion_memory_list_agent_documents.py \
  --companion-id <agent_id>
```

**仅有 `agent_id`、且只有一个 `(user_id, chat_id)`** 时可省略 scope；多 scope 时脚本会列出候选并退出，需补 `--user-id` / `--chat-id`，或加 **`--all-scopes`** 遍历全部。

### 常用参数

| 参数 | 作用 |
|------|------|
| `--companion-id` | WebSocket/API 的 `agent_id` |
| `--user-id` / `--chat-id` | MemoryStore 作用域三元组 |
| `--config` | 默认 `config.yaml`；本地 Ops 可用 `devops/config.yaml.local` |
| `--list-scopes` | 列出该 companion 下所有 `(user_id, chat_id)` |
| `--all-scopes` | 对该 `companion_id` 的每个 scope 各 dump 一遍 |
| `--meta-only` | 只打路径与 `sequence_id` / 字数 / `created_at`，不打正文 |
| `--json` | 每 scope 一行 JSON（`--meta-only` 时不含 `content` 字段） |
| `--output-dir DIR` | 将正文写入 `DIR/<companion_id>/<chat_id>/<相对路径>` |

### 示例

```bash
# 元数据总览（推荐先看，避免 transcript 刷屏）
PYTHONPATH=. python .cursor/skills/scripts/companion_memory_list_agent_documents.py \
  --companion-id <agent_id> --meta-only

# 全量正文到终端
PYTHONPATH=. python .cursor/skills/scripts/companion_memory_list_agent_documents.py \
  --companion-id <agent_id>

# 导出到目录
PYTHONPATH=. python .cursor/skills/scripts/companion_memory_list_agent_documents.py \
  --companion-id <agent_id> \
  --output-dir .inty/memory_dump

# 本地测试用户 + 明确 chat
PYTHONPATH=. python .cursor/skills/scripts/companion_memory_list_agent_documents.py \
  --companion-id <agent_id> \
  --user-id user-testing \
  --chat-id <chat_id> \
  --meta-only

# 该 agent 关联的所有 chat scope
PYTHONPATH=. python .cursor/skills/scripts/companion_memory_list_agent_documents.py \
  --companion-id <agent_id> --all-scopes --meta-only
```

## 实现说明

- 通过 **`get_memory_store`** + **`MemoryStore.iter_stored_relative_paths`** / **`read_document_if_exists`** 读最新正文（与线上一致）。
- 版本元数据（`sequence_id`、`created_at`）来自 **`companion_memory_document_versions`** ORM 聚合，与父技能 SQL 模板一致。

## 注意

- 大字段（`transcript.jsonl` 等）务必先用 **`--meta-only`** 或 **`--json --meta-only`**。
- REPL 的 `user_msg_uuid` / `langsmith_trace_id` **不是** `chat_id`。
