# FR_AGENTIC_MEMORY_STORE

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
