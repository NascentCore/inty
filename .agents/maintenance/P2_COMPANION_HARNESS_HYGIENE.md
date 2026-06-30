# Companion Harness Hygiene

Maintenance agents fix **one TODO per commit** when possible. Mark `claimed` with branch name before implementation.

## 2026-06-20 scan

Source: `ruff check app/core/companion_harness/ --select UP017,UP035,UP041` and vulture `--min-confidence 80`.

Open PRs checked: #3555 (app-ws channel adapter), #3556 (stale REPL/turn_engine cleanup) — no overlap.

### Open tasks

- [x] **HYGIENE-2026-01** ruff UP017: `companion/utc.py` — replace `timezone.utc` with `datetime.UTC` in canonical UTC helpers. Fixed in `cursor/agent-maintenance-tasks-48d5`.
- [x] **HYGIENE-2026-02** ruff UP035: move `Iterator` / `Awaitable` / `Callable` / `Mapping` / `Iterable` imports from `typing` to `collections.abc` in seven production modules (`dreaming_observability.py`, `turn_routes.py`, `user_time_context_llm_slice.py`, `companion_tool_runtime.py`, `dispatchers/memory_store.py`, `runtime.py`, `tool_background.py`). Fixed in `cursor/agent-maintenance-tasks-48d5`.
- [x] **HYGIENE-2026-03** ruff UP041: replace `asyncio.TimeoutError` with builtin `TimeoutError` in `agentic_companion/companion.py` and `companion/dual_llm_foreground_chat.py`. Fixed in `cursor/agent-maintenance-tasks-48d5`.
- [x] **HYGIENE-2026-04** vulture: prefix unused FakeLLMClient stub parameters (`route` → `_route`; `attempt_log_label` kept for caller keyword, bound to `_` in body) in companion-harness tests. Fixed in `cursor/agent-maintenance-tasks-48d5`.
- [x] **HYGIENE-2026-05** ruff UP017: remaining `timezone.utc` in `agentic_companion/output_queue.py`, `agentic_companion/postgres_queue.py`, `companion/dreaming.py`, `companion/proactive_chat.py`, `companion/schedule_queue.py`, `runtime/dreaming_batch.py`, `tools/fal_z_image_tool.py`. Fixed in `cursor/agent-maintenance-tasks-f49a`.
- [x] **HYGIENE-2026-06** ruff UP017: test files still using `timezone.utc` instead of `datetime.UTC` (batch by test subdir). Fixed in `cursor/agent-maintenance-tasks-f49a`.

## 2026-06-22 scan

Source: open PR overlap check (#3611 #3400 rename, #3620 #3375 ai_private.md reader); ruff UP017/UP035/UP041 + vulture `--min-confidence 80` — clean.

Open PRs checked: #3611 (INNER_TICK_MONOLOG rename #3400), #3620 (dead ai_private.md reader #3375) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-07** #3551: Dreaming batch LangSmith parent — `record_dreaming_batch_observability` on failure paths (`DreamingTranscriptBoundaryMismatchError` etc.). Fixed in `cursor/agent-maintenance-tasks-b0b1` / pull/3621.
- [x] **HYGIENE-2026-08** #3413: Export module-level `Final` MemDoc path constants in `memory_store_path_constants.py`; migrate ad-hoc `_USER_MD_REL` / `_MEMORY_REL` in `read_web_page.py`, `client_time_from_memory_store.py`, `companion_tool_runtime.py`, `image_gate.py`. Fixed in `cursor/agent-maintenance-tasks-b0b1` / pull/3621.
- [x] **HYGIENE-2026-09** #3413: Wire `memory_store_document_mapping._REL_TO_KIND` keys and `MemoryStoreScopePaths` to canonical path constants. Fixed in `cursor/agent-maintenance-tasks-b0b1` / pull/3621.

## 2026-06-23 scan

Source: issue audit `hygiene_defer` lane; ruff UP017/UP035/UP041 + vulture `--min-confidence 80` clean on `app/core/companion_harness/`.

Open PRs checked: #3611 (#3400 monolog rename), #3620 (#3375 ai_private.md reader), #3621 (HYGIENE-2026-07..09 #3551/#3413), #3622 (issue audit), #3623 (#3417 prompt_slices) — no overlap.

### Open tasks

- [x] **HYGIENE-2026-10** #3553: hoist `langsmith_slice` onto `CompanionTurnDeps`; turn + tool_background share `deps.langsmith_slice`. Fixed in `cursor/agent-maintenance-tasks-c4bb`.
- [x] **HYGIENE-2026-11** #3552: atomic `MemoryStore.append_jsonl_record` (store lock) for concurrent user-feedback appends. Fixed in `cursor/agent-maintenance-tasks-c4bb`.
- [x] **HYGIENE-2026-12** #3550: Postgres `pg_try_advisory_lock` per scope in `run_dreaming_batch_if_due`; skip + observability on contention. Fixed in `cursor/agent-maintenance-tasks-c4bb`.

## 2026-06-24 scan

Source: open PR overlap check (#3658 zero-reference dead symbols); ruff UP017/UP035/UP041 + vulture `--min-confidence 80` clean; ruff F401/F841 on harness + tests.

Open PRs checked: #3658 (dead symbols DREAMING_BATCH_ORCHESTRATOR / flush_now) — no overlap.

### Open tasks

- [x] **HYGIENE-2026-13** ruff F841: remove unused `bootstrap_interim_output_sink` local in `companion/turn.py`. Fixed in `cursor/agent-maintenance-tasks-8357`.
- [x] **HYGIENE-2026-14** #3504: rename OutputQueue DB column `in_reply_to_input_ids_json` → `message_ids_json` (Alembic + ORM + repository). Fixed in `cursor/agent-maintenance-tasks-8357`.
- [x] **HYGIENE-2026-15** ruff F401: remove unused `json` import in `tests/.../test_memory_store.py`. Fixed in `cursor/agent-maintenance-tasks-8357`.
- [x] **HYGIENE-2026-16** #3413 follow-up: seed core templates from `memory_store_path_constants` rel paths instead of `_CORE_COMPANION_TEMPLATE_ATTRS` attr-name tuple. Fixed in `cursor/agent-maintenance-tasks-8357`.

## 2026-06-25 scan

Source: open PR overlap check (#3682 guidelines rename only); ruff UP017/UP035/UP041/F401/F841 + vulture `--min-confidence 80` clean on `app/core/companion_harness/`.

Open PRs checked: #3682 (`.agents/guidelines` rename) — no overlap.

### Open tasks

- [x] **HYGIENE-2026-17** #3413: `companion_user_feedback.py` snapshot paths + transcript from `memory_store_path_constants`. Fixed in `cursor/agent-maintenance-tasks-471f`.
- [x] **HYGIENE-2026-18** #3413: `companion_tool_definitions.py` write allowlists from canonical path constants. Fixed in `cursor/agent-maintenance-tasks-471f`.
- [x] **HYGIENE-2026-19** #3413: `user_md_identity.py` import `USER_MD_REL` from `memory_store_path_constants` (drop duplicate). Fixed in `cursor/agent-maintenance-tasks-471f`.

## 2026-06-26 scan

Source: open PR overlap check (#3716 `MemoryStore.append_line` removal); ruff UP017/UP035/UP041/F401/F841 + vulture `--min-confidence 80` on `app/core/companion_harness/` + tests.

Open PRs checked: #3716 (`append_line` dead path) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-20** ruff F401: `user_md_identity.py` — re-export `USER_MD_REL` from `memory_store_path_constants` (HYGIENE-2026-19 left import without public re-export). Fixed in `cursor/agent-maintenance-tasks-9bc3` / pull/3717.
- [x] **HYGIENE-2026-21** ruff F401: remove unused `TurnRuntimeContext` import in `tests/.../test_companion_drain_scripted_llm.py`. Fixed in `cursor/agent-maintenance-tasks-9bc3` / pull/3717.
- [x] **HYGIENE-2026-22** ruff UP017: remaining `timezone.utc` in `test_harness_orchestration_scripted_llm.py`, `test_turn_tail_user.py`, `test_projection_stubs.py`. Fixed in `cursor/agent-maintenance-tasks-9bc3` / pull/3717.

## 2026-06-27 scan

Source: open PR overlap check (#3716 append_line removal); ruff UP017/UP035/UP041/F401/F841 + vulture `--min-confidence 80` clean on `app/core/companion_harness/` + tests.

Open PRs checked: #3716 (`append_line` dead path) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-23** #3413: `image_gate.py` — use `GENERATED_IMAGES_INDEX_JSONL_REL` from `memory_store_path_constants` (drop `_IMAGE_ASSET_INDEX_REL`). Fixed in `cursor/agent-maintenance-tasks-3d69` / pull/3719.
- [x] **HYGIENE-2026-24** #3413: `ai_private_prompt.py` — import `AI_PRIVATE_JSONL_REL` from `memory_store_path_constants` (drop duplicate). Fixed in `cursor/agent-maintenance-tasks-3d69` / pull/3719.
- [x] **HYGIENE-2026-25** #3413: `companion_tool_definitions.py` — replace `AI_PRIVATE_JSONL_RELATIVE_PATH` with canonical `AI_PRIVATE_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-3d69` / pull/3719.

## 2026-06-28 scan

Source: open PR overlap check (#3716 `MemoryStore.append_line` removal); ruff UP017/UP035/UP041/F401/F841 + vulture `--min-confidence 80` clean on `app/core/companion_harness/` + tests; #3413 follow-up — harness modules still import `*_RELATIVE_PATH` from `living_sphere` / `techno_core` models or duplicate dot-prefixed JSONL literals.

Open PRs checked: #3716 (`append_line` dead path) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-26** #3413: `companion_tool_runtime.py` — use `TECHNO_CORE_EVENTS_JSONL_REL` / `LIVING_SPHERE_UPDATES_JSONL_REL` from `memory_store_path_constants` (drop model `*_RELATIVE_PATH` imports). Fixed in `cursor/agent-maintenance-tasks-cac4` / pull/3722.
- [x] **HYGIENE-2026-27** #3413: `companion_tool_definitions.py` — same canonical path constants in tool descriptions. Fixed in `cursor/agent-maintenance-tasks-cac4` / pull/3722.
- [x] **HYGIENE-2026-28** #3413: `living_sphere_curator.py` — use `LIVING_SPHERE_MD_REL` / `LIVING_SPHERE_UPDATES_JSONL_REL` from `memory_store_path_constants`. Fixed in `cursor/agent-maintenance-tasks-cac4` / pull/3722.
- [x] **HYGIENE-2026-29** #3413: add `COMPANION_RUNTIME_EVENTS_JSONL_REL` to `memory_store_path_constants`; migrate `runtime_events.py` + `memory_store_document_mapping`. Fixed in `cursor/agent-maintenance-tasks-cac4` / pull/3722.
- [x] **HYGIENE-2026-30** #3413: add `COMPANION_USER_FEEDBACK_JSONL_REL` to `memory_store_path_constants`; migrate `companion_user_feedback.py` + `memory_store_document_mapping`. Fixed in `cursor/agent-maintenance-tasks-cac4` / pull/3722.

## 2026-06-29 scan

Source: open PR overlap check (#3716 `MemoryStore.append_line` removal); ruff UP017/UP035/UP041/F401/F841 + vulture `--min-confidence 80` clean on `app/core/companion_harness/` + tests; #3413 follow-up — harness modules still use scattered `context.json` / `transcript.jsonl` / `tool_background.jsonl` literals.

Open PRs checked: #3716 (`append_line` dead path) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-31** #3413: `lifecycle_invariants.py` — `AWAKE_TURN_ALLOWED_APPEND_JSONL` + `AWAKE_TURN_TOOL_BACKGROUND_LOG_JSONL` from `memory_store_path_constants`. Fixed in `cursor/agent-maintenance-tasks-20fc` / pull/3725.
- [x] **HYGIENE-2026-32** #3413: `companion_tool_runtime.py` — transcript rel guard from canonical path constants. Fixed in `cursor/agent-maintenance-tasks-20fc` / pull/3725.
- [x] **HYGIENE-2026-33** #3413: `tool_background.py` — `append_jsonl_record` uses `TOOL_BACKGROUND_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-20fc` / pull/3725.
- [x] **HYGIENE-2026-34** #3413: `models.py` — `load_context_meta` + `transcript_jsonl_rel_for_turn` from canonical constants. Fixed in `cursor/agent-maintenance-tasks-20fc` / pull/3725.
- [x] **HYGIENE-2026-35** #3413: `bootstrap.py`, `manager.py`, `agentic_companion/turn.py` — `CONTEXT_JSON_REL` (drop inline TODOs). Fixed in `cursor/agent-maintenance-tasks-20fc` / pull/3725.
- [x] **HYGIENE-2026-36** #3413: `inner_tick_schedule.py`, `proactive_chat.py` — `TRANSCRIPT_JSONL_REL` for transcript projection loads. Fixed in `cursor/agent-maintenance-tasks-20fc` / pull/3725.

## 2026-06-30 scan

Source: open PR overlap check (#3716 `append_line` removal); ruff UP017/UP035/UP041/F401/F841 + vulture `--min-confidence 80` clean on `app/core/companion_harness/` + tests; #3413 follow-up — production modules still use hardcoded MemDoc path strings in dreaming curation and prompt bundle load.

Open PRs checked: #3716 (`append_line` dead path) — no overlap with tasks below.

### Open tasks

- [ ] **HYGIENE-2026-37** #3413: `dreaming_consolidation.py` — `read_document` / `write_document` paths from `memory_store_path_constants`. **claimed** `cursor/agent-maintenance-tasks-eaf7`.
- [ ] **HYGIENE-2026-38** #3413: `models.py` — `load_prompt_bundle_from_store` MemDoc paths from canonical constants. **claimed** `cursor/agent-maintenance-tasks-eaf7`.
- [ ] **HYGIENE-2026-39** #3413: add dot-prefixed state JSON `*_REL` constants; wire `memory_store_document_mapping.py` + `MemoryStoreScopePaths`. **claimed** `cursor/agent-maintenance-tasks-eaf7`.
