---
name: inspect-companion-harness
description: >-
  For humans to understand the companion runtime's foundational working conditions. Inspect companion harness persistence in Postgres (MemoryStore document versions).
  Covers companion_memory_document_versions, scope triples, and SQL templates for
  identity/transcript/context, etc. Load DB credentials from repo config.yaml. Sub-skill
  for reading context_mode only: context-mode-in-db/SKILL.md.
---

# Inty companion：核对 MemoryStore 与 Postgres 落库

## Sub-skills

- **`context-mode-in-db/SKILL.md`**：只查 **`context.json`** 落库里的 **`context_mode`** / **`post_bootstrap_context_mode`**（`document_kind = context_json`），按 **`agent_id`（`companion_id`）** 排查体验配置。

## 何时使用

- 用户问「`IDENTITY.md` / 工作区文档有没有写进数据库」「工具更新了语料但库里看不到」。
- 对照 LangSmith trace 里的 `memory_store_write_document` / `companion_update_prompt_slice` 与真实 DB 行。
- 验证本地/开发环境 **append-only** 版本表是否出现 **新 `sequence_id`**。

## 配置里取连接信息

1. 仓库根目录读取 **`/config.yaml`**（若无则用 **`/devops/config.yaml.local`**；跑 pytest / CI 常见 **`/devops/config.yaml.test`**）。
2. 使用块 **`database`**：`host`、`port`、`user`、`password`、`db`。
3. 用 **`psql`** 或任意 Postgres 客户端连接；shell 示例：`PGPASSWORD='<password>' psql -h <host> -p <port> -U <user> -d <db>`。

不要在无关对话里复述口令全文；技能执行时可从文件读取。

## 表与语义（单一事实来源在代码）

- **表名**：`companion_memory_document_versions`
- **ORM**：`/app/models/companion_memory_documents.py` · `CompanionMemoryDocumentVersion`
- **逻辑正文（折叠）**：同一 `(user_id, companion_id, chat_id, document_kind[, calendar_date])` 下，按 **`sequence_id` 升序** 扫描所有行：`content_mode = snapshot` 时 **`content` 替换**当前累积正文；`content_mode = suffix` 时 **`content` 拼接到**正文末尾（`append_line` / `append_jsonl_record` 的真追加）。**只看 `sequence_id` 最大的一行**在存在 `suffix` 时**不等于**全文。根目录稿的 **`calendar_date` 为 NULL**；**`memory/daily/YYYY-MM-DD.md` / `memory/YYYY-MM-DD.md`** 对应 **`memory_daily_raw` / `memory_day_summary`**，查某日时 **`WHERE calendar_date = DATE 'YYYY-MM-DD'`**。
- **`document_kind` ↔ 逻辑路径**：`/app/core/companion_harness/memory/memory_store_document_mapping.py`（例：`IDENTITY.md` → **`identity`**，`context_json` ↔ `context.json`，`transcript` ↔ `transcript.jsonl`）。

## 作用域三元组怎么对齐

- **`companion_id`**：HTTP/API/WebSocket 里的 **`agent_id` 原样**（见 `/app/core/companion_harness/companion/AGENTS.md`）。
- **`user_id`**：认证用户 id（本地测试常见 **`user-testing`**，以 JWT / 服务端日志为准）。
- **`chat_id`**：该用户与该 `agent_id` 会话对应的数据库 **`chats.id`**（字符串主键）；若未知，可对版本表 **`DISTINCT chat_id`**，或查 **`chats`**：`WHERE user_id = … AND agent_id = …`（见 `/app/models/chat.py`）。

REPL 日志里的 `langsmith_trace_id` / `user-input message-uuid` **不是** `chat_id`；后者须从 DB 或会话上下文取得。

**仅在已知 user + companion 时列出曾有写入的 chat_id（缩小排查范围）**

```sql
SELECT DISTINCT chat_id
FROM companion_memory_document_versions
WHERE user_id = '<user_id>' AND companion_id = '<companion_id>'
ORDER BY chat_id;
```

## SQL 模板（按需替换占位符）

**最新一条 identity（推荐先做）**

```sql
SELECT sequence_id, created_at, content_mode,
       LENGTH(content) AS content_chars,
       content LIKE '%YOUR_SNIPPET%' AS has_snippet
FROM companion_memory_document_versions
WHERE user_id = '<user_id>'
  AND companion_id = '<companion_id>'
  AND chat_id = '<chat_id>'
  AND document_kind = 'identity'
ORDER BY sequence_id DESC
LIMIT 5;
```

（`identity` 等整篇覆盖稿多为 **snapshot**；`transcript` 等可出现 **suffix**，勿用「最后一行」当全文。）

**某 scope 下近期所有文档种类**

```sql
SELECT document_kind, MAX(sequence_id) AS max_seq, MAX(created_at) AS last_at
FROM companion_memory_document_versions
WHERE user_id = '<user_id>' AND companion_id = '<companion_id>' AND chat_id = '<chat_id>'
GROUP BY document_kind
ORDER BY document_kind;
```

**拉 identity 最近一次写入的正文片段（建议同时看 `content_mode`）**

```sql
SELECT content_mode, LEFT(content, 1500) FROM companion_memory_document_versions
WHERE user_id = '<user_id>' AND companion_id = '<companion_id>' AND chat_id = '<chat_id>'
  AND document_kind = 'identity'
ORDER BY sequence_id DESC LIMIT 1;
```

## 进程内 MemoryStore 与 DB 的关系（排错）

- 生产路径下，带 repository 的 `MemoryStore` 由 **`/app/core/companion_harness/memory/memory_registry.py`** 注册：键为 **`CompanionScope.registry_key()`**（`user_id:companion_id:chat_id`）；`get_memory_store(scope, dsn=...)` 返回的实例与 `CompanionManager` 会话内 `session.store` 为同一 ORM 面，工具线程通过 `MemoryStore` 引用或 runtime inspect overlay 对齐写入。
- 若 DB 无新行但工具返回 OK：先确认 **后端已加载含该改动的代码** 且 **会话已用 DSN 创建 store**；再用上文 SQL 核对。

## 可选交叉验证

- **LangSmith**：trace 内搜 `companion_update_prompt_slice` / `memory_store_write_document` 及对 `IDENTITY.md` 的路径参数；见仓库 **`.cursor/skills/langsmith-download-run/SKILL.md`**。

## 文档引用（人类读者）

- 持久化约定：**`/app/core/companion_harness/companion/AGENTS.md`**「持久化与数据表」「进程内 registry」小节。
