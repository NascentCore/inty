---
name: inspect-companion-harness-context-mode-in-db
description: >-
  Read the companion session experience profile from Postgres: context.json fields
  context_mode and post_bootstrap_context_mode in companion_memory_document_versions
  (document_kind context_json). Use when debugging bootstrap vs settled profile for a
  given agent_id (companion_id). Same config.yaml database block as parent skill.
---

# Companion：从数据库读 `context_mode`

**父技能**：上一级目录 **`../SKILL.md`**（`inspect-companion-harness` 根技能）。

## 何时使用

- 用户给出 **`agent_id`**（即 MemoryStore 作用域里的 **`companion_id`**），要核对库里持久化的 **`context_mode`** / **`post_bootstrap_context_mode`**。
- 与 WS `meta_data.context_mode` 或 LangSmith 里 companion 上下文对不上时，以 **DB 最新 `context_json` 行** 为准。

## 连接与表（与父技能一致）

- **`config.yaml`** 的 **`database`** 块；用 **`psql`** 连接。
- **表**：`companion_memory_document_versions`
- **逻辑文档**：`context.json` → **`document_kind = 'context_json'`**；根级文档 **`calendar_date IS NULL`**。

## 仅有 `agent_id` 时：先列出现过的 `chat_id`

```sql
SELECT DISTINCT user_id, chat_id
FROM companion_memory_document_versions
WHERE companion_id = '<agent_id>'
ORDER BY user_id, chat_id;
```

## 读某作用域下最新体验配置（推荐）

将 `trim(content)` 当 JSON 解析，取出 `context_mode` 与可选的 `post_bootstrap_context_mode`（bootstrap 会话常见）。

```sql
SELECT sequence_id,
       created_at,
       trim(content)::json->>'context_mode' AS context_mode,
       trim(content)::json->>'post_bootstrap_context_mode' AS post_bootstrap_context_mode,
       length(trim(content)) AS content_chars
FROM companion_memory_document_versions
WHERE user_id = '<user_id>'
  AND companion_id = '<agent_id>'
  AND chat_id = '<chat_id>'
  AND document_kind = 'context_json'
  AND calendar_date IS NULL
ORDER BY sequence_id DESC
LIMIT 10;
```

**最新一条**（只看当前持久化状态）：把 `LIMIT` 改为 **`LIMIT 1`**。

## 仅有 `agent_id`、要看所有 chat 各自的最新状态

```sql
SELECT DISTINCT ON (user_id, chat_id)
       user_id,
       chat_id,
       sequence_id,
       created_at,
       trim(content)::json->>'context_mode' AS context_mode,
       trim(content)::json->>'post_bootstrap_context_mode' AS post_bootstrap_context_mode
FROM companion_memory_document_versions
WHERE companion_id = '<agent_id>'
  AND document_kind = 'context_json'
  AND calendar_date IS NULL
ORDER BY user_id, chat_id, sequence_id DESC;
```

## 语义（代码真源）

- 体验配置 id 存 **`context.json`** 的 **`context_mode`**；**`post_bootstrap_context_mode`** 仅在 **`context_mode = bootstrap`** 等过渡阶段有意义；见 **`app/core/companion_harness/experience_profile.py`** 与 **`ContextMeta`**（`app/core/companion_harness/companion/models.py`）。

## 注意

- **`context.json`** 的更新路径为整篇 **`snapshot`**，`ORDER BY sequence_id DESC LIMIT 1` 解析 JSON 仍成立；**`transcript` 等**若含 **`suffix`** 行，不能以「最后一行 `content`」当全文（见父技能「逻辑正文（折叠）」）。
- **`agents`** 表不负责存 **`context_mode`**；以 **`context_json`** 版本为准。
- 若 **`trim(content)::json`** 报错，先 **`SELECT sequence_id, left(content, 500)`** 看正文是否被截断或非 JSON。
