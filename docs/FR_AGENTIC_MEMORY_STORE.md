# FR_AGENTIC_MEMORY_STORE

## 中文执行计划

本 FR 目标：为 agentic companion 提供可持久化的命名记忆、可审计来源、层次结构、PostgreSQL + pgvector 向量检索与全文混合检索、进程内运行时缓存，以及与其它提示词切片统一的 LLM 上下文组装能力。

### 前置决策（阶段 0）

- 在 **扩展现有 `memory` 表（方案 A）** 与 **新建 `agentic_memory` 等表（方案 B，本文默认）** 之间定案；避免与节日/日常抽取语义纠缠者选 B。
- 固化 **作用域键**：`user_id` 必选；`agent_id` / `chat_id` 是否参与过滤与唯一约束写清。
- 固化 **嵌入合同**：模型 id、向量维度、是否归一化、距离算子（与 HNSW opclass 一致）、`embedding_version` 升级与全量重算策略。

### 分阶段交付

| 阶段 | 中文说明 | 主要产出 |
|------|----------|----------|
| 0 | 决策与契约 | 方案 A/B、作用域与嵌入合同文档化 |
| 1 | 数据库 | Alembic：`CREATE EXTENSION vector`、新表、B-tree / HNSW / GIN 索引 |
| 2 | 数据访问层 | SQLAlchemy 模型、Repository、嵌入失败状态与重试钩子 |
| 3 | 写入流水线 | 提炼 -> 归一化/去重 -> 调嵌入 API -> 同事务写主表与 provenance -> 通知缓存失效 |
| 4 | 运行时内存 | 工作集、热点 LRU、写合并；**以 PG 为准**，进程可冷启动重建 |
| 5 | 检索服务 | 过滤后向量 Top-K + 全文 Top-K -> RRF/加权融合 -> 可选重排；层次打包进 token 预算 |
| 6 | 提示词组装 | 记忆单独成块注入；顺序：静态系统 -> 工具策略 -> **记忆** -> 近期对话；各层 max_tokens |
| 7 | 对外 API（若需要） | HTTP 契约；同步 `app/schemas` 与 Kotlin `api/model` |
| 8 | 质量与观测 | 集成测试、回归（旧 `memory` 不受影响）、延迟与嵌入失败率指标 |
| 9 | 上线 | 功能开关、重嵌入与索引重建运维说明 |

### 关键依赖与风险

- **依赖**：带 pgvector 的 Postgres 镜像或实例；嵌入服务配额与密钥；与 `companion_chat_service` 的 `memory_pg_dsn` 是否共用。
- **风险**：大表 HNSW 构建窗口；过滤过窄时预过滤与召回需调参；来源字段含 PII 须与聊天记录同等留存与权限；检索需防跨租户（禁止仅按向量查）。

### 详细英文规格

以下各节为与实现对齐的英文规格说明（表结构字段、流水线细节、仓库路径引用等）。

## Goal

Design and implement a persistent memory mechanism for agentic companion runtime that:

1. Stores each memory with a stable human-readable **name** (slug within scope) and **provenance** (which conversation fragments and metadata justified the extraction).
2. Supports **hierarchical** organization (tree or DAG via `parent_id` and optional edge table).
3. Persists in **PostgreSQL** with the **pgvector** extension for semantic similarity search, plus **full-text** (or keyword) retrieval for hybrid ranking.
4. Provides an **in-process runtime** layer (cache, working set, write coalescing) backed by Postgres as source of truth.
5. Feeds a **prompt assembly** slot that composes retrieved memories with static prompt slices and other slices (tools, mode, transcript) for the LLM.

This document is the execution-oriented spec. Schema and table names below are proposals until reviewed against existing tables.

## Relationship to existing systems

### Existing `memory` table (extraction pipeline)

- Alembic: `alembic/versions/20260127_120000_add_memory_tables.py`.
- Columns today: `user_id`, `memory_type` (`user_common` | `user_agent`), `agent_id`, `content`, `extracted_at`, etc.
- Later migrations add delivery, metadata, festival fields (see `alembic/versions/` under `memory`).

**Decision required (Phase 0):**

- **Option A - Evolve**: extend `memory` with `name`, `parent_id`, `embedding`, provenance child table, FTS. Risk: coupling to festival/daily extraction semantics and migrations.
- **Option B - New tables** (recommended for clarity): e.g. `agentic_memory` + `agentic_memory_provenance` (+ optional `agentic_memory_edge`). Keeps festival/daily rows unchanged; companion LTM is explicit.

This FR assumes **Option B** unless product explicitly merges both lifecycles.

### Companion runtime memory (workspace / kernel)

- Code: `app/core/agentic_kernel/companion/memory_store.py`, `memory_registry.py`, used from `turn_engine.py` and `companion_chat_service.py` (`memory_pg_dsn`).
- Today: workspace-scoped store for compaction and related state; not a substitute for long-term named vector memory unless extended.

**Integration:** add a thin **read-through / write-through** adapter from kernel turn path to Postgres-backed LTM, or a dedicated `AgenticMemoryRuntime` that shares DSN with `SqlAlchemyMemoryRepository` patterns. Process restart must rebuild in-memory indexes from PG.

### Prompt assembly

- Related: `docs/FR_CLEAN_AGENT_PROMPTS_SYSTEM.md` (typed assembly, slice boundaries).
- Memory slice should be a **single injected block** built by a small `PromptAssembler` or equivalent, not ad hoc string concat in multiple call sites.

## Storage choice

- **PostgreSQL + pgvector**: one transactional store for metadata, provenance, ACL filters, and vectors. Aligns with `backend/ARCH.md`, `backend/AGENTS.md`, and `docker compose up pgvector`.
- **Hybrid retrieval**: `embedding <=> query_embedding` (or `<->` / cosine per normalization contract) plus `tsvector` + GIN for lexical channel; merge with RRF or weighted scores.

## Proposed logical data model

### Table: `agentic_memory` (name illustrative)

| Column | Purpose |
|--------|---------|
| `id` | UUID or BIGSERIAL primary key |
| `user_id` | Tenant; mandatory on every query |
| `agent_id` | Nullable if memory is user-global; else scoped to companion/agent |
| `chat_id` | Optional finer scope for session-bound memories |
| `parent_id` | Hierarchy; NULL for root |
| `name` | Slug unique per `(user_id, agent_id, chat_id)` scope (exact rules in migration) |
| `content` | Text shown to LLM as the memory body |
| `embedding` | `vector(N)`; N fixed per `embedding_model` |
| `embedding_model` | Model id string |
| `embedding_version` | Integer or string for re-embed campaigns |
| `content_tsv` | Generated `tsvector` from `content` (+ optional `name`) |
| `valid_from`, `valid_to` | Soft delete / supersession |
| `created_at`, `updated_at` | Audit |

Indexes (illustrative):

- B-tree: `(user_id)`, `(user_id, agent_id)`, `(user_id, agent_id, parent_id)`.
- Unique: `(user_id, agent_id, name)` where `agent_id` is nullable use partial indexes or surrogate scope key.
- HNSW on `embedding` with operator class matching distance used in queries.
- GIN on `content_tsv`.

### Table: `agentic_memory_provenance`

| Column | Purpose |
|--------|---------|
| `id` | PK |
| `memory_id` | FK to `agentic_memory` |
| `source_type` | e.g. `chat_message`, `chat_window`, `tool`, `document` |
| `source_id` | External id (message id, chat id, chunk id) |
| `excerpt` | Truncated raw text optional |
| `meta` | JSONB for extractor version, prompt hash, offsets |

### Optional: `agentic_memory_edge`

- For non-tree relations: `related_to`, `supersedes`, `derived_from` with `(from_id, to_id, kind)`.

## In-process runtime subsystem

Responsibilities:

1. **Working set**: last-N turns or pending writes not yet visible to retriever.
2. **Hot cache**: subset of embeddings for active `user_id` / `agent_id` (LRU or explicit pin for session duration).
3. **Write queue**: debounce duplicate upserts by `name`; batch embed API calls where safe.

Rules:

- **Postgres is source of truth**; in-memory structures are disposable.
- After PG commit, update or invalidate cache entries by `id` + version.
- Startup: no mandatory warm load; lazy load on first retrieval for scope.

## Write pipeline

1. **Extract**: LLM or rule job emits structured fields (`name`, `content`, `parent_id`, provenance rows).
2. **Normalize**: trim name, enforce uniqueness policy, merge or bump version if same `name`.
3. **Embed**: call configured embedding provider; on failure set `embedding_status` (add column) and enqueue retry job.
4. **Persist**: single transaction: insert/update `agentic_memory`, insert provenance rows, update `content_tsv` if not generated.
5. **Notify runtime**: invalidate or patch cache.

Async: long embedding should not block user-visible chat completion; align with `defer_memory_update` patterns in `companion_chat_service.py` where applicable.

## Read / retrieval pipeline

1. Build `query_embedding` from latest user utterance or aggregated task string.
2. SQL filter: `user_id = ?` AND optional `agent_id`, `chat_id`, `valid_to IS NULL`, hierarchy constraints.
3. Vector branch: `ORDER BY embedding <=> :q LIMIT k_vec`.
4. FTS branch: `ts_rank_cd` or plain `@@` query, `LIMIT k_txt`.
5. Fuse: RRF or weighted sum; optional cross-encoder rerank on top M (feature-flagged).
6. **Hierarchy-aware pack**: include ancestor summaries + leaf details under token budget (configurable).

## Prompt assembly integration

Suggested message order (align with clean prompt system when merged):

1. Static system slices (persona, safety, format).
2. Tool / policy slices.
3. **Memory slice**: bullet or numbered list; each item: `name`, `content`, one-line provenance reference (ids only in compact mode).
4. Recent transcript window.

Token caps per slice in config; memory slice truncates lowest-ranked items first.

## HTTP / schema sync

If mobile or ops clients list or edit memories:

- Update `app/schemas` and Kotlin models under `android_app/core/data/src/main/kotlin/ai/sxwl/android/data/api/model` per repo convention.

## Security

- Every read path must include **tenant filter** (`user_id`); never retrieve by vector alone.
- Provenance may contain PII; apply same retention and access control as chat history.
- Mitigate memory poisoning: diversity in top-K, confidence flags, optional human review queue for high-impact writes.

## Testing

1. Migration: fresh DB `alembic upgrade head`; extension `vector` present.
2. Repository integration tests: insert, hybrid search, uniqueness, parent chain, supersede.
3. Regression: existing `memory` extraction and APIs unchanged when using Option B tables.
4. Load smoke: fixed row count, assert p95 below agreed threshold on CI-sized DB.

## Execution phases (checklist)

| Phase | Deliverable |
|-------|-------------|
| 0 | Choose Option A vs B; document scope keys and embedding contract |
| 1 | Alembic revision: `CREATE EXTENSION vector`, new tables, indexes |
| 2 | SQLAlchemy models + repository + `embedding_status` / retry worker hook |
| 3 | Write pipeline: extract -> normalize -> embed -> persist -> cache invalidate |
| 4 | `AgenticMemoryRuntime` (or extend `MemoryStore`) read/write-through |
| 5 | Hybrid search API (internal service first; HTTP if required) |
| 6 | Prompt memory slice + token budget in companion / kernel assembly path |
| 7 | Client schemas if user-facing CRUD |
| 8 | Tests + observability (latency, embed failures, queue depth) |
| 9 | Rollout: feature flag; runbook for re-embed and index rebuild |

## References (repo paths)

- `alembic/versions/20260127_120000_add_memory_tables.py` - existing `memory` table
- `alembic/AGENTS.md` - migration workflow
- `app/core/agentic_kernel/companion/memory_store.py` - runtime store
- `app/services/companion_chat_service.py` - `memory_pg_dsn`, defer patterns
- `docs/FR_CLEAN_AGENT_PROMPTS_SYSTEM.md` - prompt assembly direction
- `backend/ARCH.md`, `backend/AGENTS.md` - pgvector / compose notes
