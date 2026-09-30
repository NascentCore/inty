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

- [x] **HYGIENE-2026-37** #3413: `dreaming_consolidation.py` — `read_document` / `write_document` paths from `memory_store_path_constants`. Fixed in `cursor/agent-maintenance-tasks-eaf7` / pull/3728.
- [x] **HYGIENE-2026-38** #3413: `models.py` — `load_prompt_bundle_from_store` MemDoc paths from canonical constants. Fixed in `cursor/agent-maintenance-tasks-eaf7` / pull/3728.
- [x] **HYGIENE-2026-39** #3413: add dot-prefixed state JSON `*_REL` constants; wire `memory_store_document_mapping.py` + `MemoryStoreScopePaths`. Fixed in `cursor/agent-maintenance-tasks-eaf7` / pull/3728.

## 2026-07-01 scan

Source: open PR overlap check (#3716 `MemoryStore.append_line` removal); ruff UP017/UP035/UP041/F401/F841 + vulture `--min-confidence 80` clean on `app/core/companion_harness/` + tests; #3413 follow-up — bootstrap seed rels, template seed filenames, harness tests still import `*_RELATIVE_PATH` from `living_sphere` / `techno_core`.

Open PRs checked: #3716 (`append_line` dead path) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-40** #3413: `bootstrap.py` — `_BOOTSTRAP_TEMPLATE_SEED_ONLY_RELS` from `MEMORY_MD_REL` / `SOUL_MD_REL`. Fixed in `cursor/agent-maintenance-tasks-13af` / pull/3731.
- [x] **HYGIENE-2026-41** #3413: `memory_store_scope.py` — `_PACKAGE_PROMPT_SEED_FILES` MemDoc filenames from canonical path constants. Fixed in `cursor/agent-maintenance-tasks-13af` / pull/3731.
- [x] **HYGIENE-2026-42** #3413: harness tests — `LIVING_SPHERE_RELATIVE_PATH` → `LIVING_SPHERE_MD_REL` (3 files). Fixed in `cursor/agent-maintenance-tasks-13af` / pull/3731.
- [x] **HYGIENE-2026-43** #3413: `test_techno_core_runtime.py` — `TECHNO_CORE_RELATIVE_PATH` → `TECHNO_CORE_MD_REL`. Fixed in `cursor/agent-maintenance-tasks-13af` / pull/3731.

## 2026-07-02 scan

Source: open PR overlap check (#3748 Telegram Business promotion — no harness overlap); ruff UP017/UP035/UP041/F401/F841 + vulture `--min-confidence 80` clean on `app/core/companion_harness/` + tests; #3413 follow-up — two production modules still import `*_REL` from `memory_store_scope` re-exports; harness tests still seed/read MemDoc paths as string literals.

Open PRs checked: #3748 (`cursor/telegram-business-promotion-doc-e953`) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-44** #3413: `read_web_page.py` — import `MEMORY_MD_REL` from `memory_store_path_constants` (drop `memory_store_scope` re-export). Fixed in `cursor/agent-maintenance-tasks-4be2` / pull/3749.
- [x] **HYGIENE-2026-45** #3413: `client_time_from_memory_store.py` — import `USER_MD_REL` from `memory_store_path_constants`. Fixed in `cursor/agent-maintenance-tasks-4be2` / pull/3749.
- [x] **HYGIENE-2026-46** #3413: `test_tool_background_transcript_metadata.py` — `TRANSCRIPT_JSONL_REL` for seed + read. Fixed in `cursor/agent-maintenance-tasks-4be2` / pull/3749.
- [x] **HYGIENE-2026-47** #3413: `test_ai_private_append_tool.py` — `AI_PRIVATE_JSONL_REL` for read assertion. Fixed in `cursor/agent-maintenance-tasks-4be2` / pull/3749.
- [x] **HYGIENE-2026-48** #3413: `test_read_web_page_tool.py` — `MEMORY_MD_REL` for read assertion. Fixed in `cursor/agent-maintenance-tasks-4be2` / pull/3749.
- [x] **HYGIENE-2026-49** #3413: `test_tool_background_langsmith_channel.py` — seed store paths from canonical constants. Fixed in `cursor/agent-maintenance-tasks-4be2` / pull/3749.
- [x] **HYGIENE-2026-50** #3413: `test_langsmith_turn_parent.py` — seed store paths from canonical constants. Fixed in `cursor/agent-maintenance-tasks-4be2` / pull/3749.

## 2026-07-03 scan

Source: open PR overlap check (#3748 Telegram Business promotion — no harness overlap); ruff UP017/UP035/UP041/F401/F841 + vulture `--min-confidence 80` clean on `app/core/companion_harness/` + tests; #3413 follow-up — harness tests still seed/read MemDoc paths as string literals.

Open PRs checked: #3748 (`cursor/telegram-business-promotion-doc-e953`) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-51** #3413: `test_turn_async_dual_llm.py` — `CONTEXT_JSON_REL` + `TRANSCRIPT_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-0420` / pull/3750.
- [x] **HYGIENE-2026-52** #3413: `test_companion_user_feedback_tool.py` — `CONTEXT_JSON_REL` + `TRANSCRIPT_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-0420` / pull/3750.
- [x] **HYGIENE-2026-53** #3413: `test_agentic_loop_output_queue.py` + `context_builder_test_support.py` — `TRANSCRIPT_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-0420` / pull/3750.
- [x] **HYGIENE-2026-54** #3413: `test_proactive_chat.py` — `TRANSCRIPT_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-0420` / pull/3750.

## 2026-07-04 scan

Source: open PR overlap check (#3748 Telegram Business promotion, #3751 dead `select_tail_splice_thoughts` — no harness overlap); ruff UP017/UP035/UP041/F401/F841 + vulture `--min-confidence 80` clean on `app/core/companion_harness/` + tests; #3413 follow-up — harness tests and test support still seed/read MemDoc paths as string literals.

Open PRs checked: #3748 (`cursor/telegram-business-promotion-doc-e953`), #3751 (`cursor/stale-companion-harness-code-24ac`) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-55** #3413: `companion_scripted_llm.py` — `CONTEXT_JSON_REL`, `TRANSCRIPT_JSONL_REL`, `TRANSCRIPT_INNER_TICK_JSONL_REL`, `TOOL_BACKGROUND_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-8160` / pull/3752.
- [x] **HYGIENE-2026-56** #3413: `test_prompt_builder.py` — `CONTEXT_JSON_REL`. Fixed in `cursor/agent-maintenance-tasks-8160` / pull/3752.
- [x] **HYGIENE-2026-57** #3413: `companion/test_bootstrap.py` — `CONTEXT_JSON_REL`. Fixed in `cursor/agent-maintenance-tasks-8160` / pull/3752.
- [x] **HYGIENE-2026-58** #3413: `companion/test_models.py` — `TRANSCRIPT_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-8160` / pull/3752.

## 2026-07-05 scan

Source: open PR overlap check (#3748 Telegram Business promotion, #3751 dead `select_tail_splice_thoughts`, #3753 open-objective doc — no harness overlap); ruff UP017/UP035/UP041/F401/F841 + vulture `--min-confidence 80` clean on `app/core/companion_harness/` + tests; #3413 follow-up — harness tests still seed/read MemDoc paths as string literals.

Open PRs checked: #3748 (`cursor/telegram-business-promotion-doc-e953`), #3751 (`cursor/stale-companion-harness-code-24ac`), #3753 (`cursor/open-objective-agent-doc-19af`) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-59** #3413: `test_ai_private_prompt.py` — `AI_PRIVATE_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-17c9` / pull/3754.
- [x] **HYGIENE-2026-60** #3413: `test_bootstrap_transcript_order.py` — `CONTEXT_JSON_REL` + `TRANSCRIPT_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-17c9` / pull/3754.
- [x] **HYGIENE-2026-61** #3413: `test_bootstrap_complete_not_blocked_without_profile.py` — `CONTEXT_JSON_REL`. Fixed in `cursor/agent-maintenance-tasks-17c9` / pull/3754.
- [x] **HYGIENE-2026-62** #3413: `test_ai_private_manifest_persist.py` — `CONTEXT_JSON_REL` + `TRANSCRIPT_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-17c9` / pull/3754.
- [x] **HYGIENE-2026-63** #3413: `test_dreaming.py` — `TRANSCRIPT_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-17c9` / pull/3754.
- [x] **HYGIENE-2026-64** #3413: `test_inner_tick_schedule.py` — `CONTEXT_JSON_REL` + `TRANSCRIPT_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-17c9` / pull/3754.

## 2026-07-06 scan

Source: open PR overlap check (none open); ruff UP017/UP035/UP041/F401/F841 + vulture `--min-confidence 80` clean on `app/core/companion_harness/` + tests; #3413 follow-up — harness tests still seed/read MemDoc paths as string literals.

Open PRs checked: none — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-65** #3413: `test_turn_tracks.py` — `CONTEXT_JSON_REL`. Fixed in `cursor/agent-maintenance-tasks-e621` / pull/3763.
- [x] **HYGIENE-2026-66** #3413: `test_turn_tail_user.py` — `TRANSCRIPT_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-e621` / pull/3763.
- [x] **HYGIENE-2026-67** #3413: `test_turn_pipeline_bootstrap.py` — `CONTEXT_JSON_REL` + `TRANSCRIPT_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-e621` / pull/3763.
- [x] **HYGIENE-2026-68** #3413: `test_turn_pipeline_dreaming.py` — `TRANSCRIPT_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-e621` / pull/3763.
- [x] **HYGIENE-2026-69** #3413: `test_transcript_assistant_row.py` — `TRANSCRIPT_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-e621` / pull/3763.

## 2026-07-07 scan (Stage 1 PR-5 + Stage 2 convergence)

Source: companion harness partial-convergence (`PR-5` legacy turn/downlink delete + Stage 2 typed WS emit); gate baseline green for soft orchestration + typed outbound.

Related issues: #3632 (closed), #3401 (slice 1+2 merged pull/3765–3766), #3490/#3211/#3543 (partial), #3207/#3208 (partial).

### Open tasks

- [x] **HYGIENE-2026-70** #3632: remove stale `start_tool_background_job` references in `dual_llm_foreground_chat.py` module doc and `CompanionTurnResult.tool_background_started` Field description. Fixed in Stage 1 PR-5 branch.
- [x] **HYGIENE-2026-71** #3208: remove completed emit-path TODO from `chat_ws._agent_chat_ws_completions_impl` (typed `ChatWebSocketQueuedSuccessFrame` via `build_chat_ws_queued_success_frame`). Fixed in Stage 2 branch.
- [x] **HYGIENE-2026-72** #3401: `append_turn_track_tail_user_transcript_rows` track-only (`inner_tick_kind_for_track`); dedup `turn.py` inline block; `test_turn_tail_user_track_metadata.py` (7 cases). Merged pull/3765.
- [x] **HYGIENE-2026-73** #3401 slice 2: `transcript_relative_path_for_turn_persistence`, `companion_turn_transcript_loaded_messages`, `companion_tools_for_turn`, `load_companion_turn_state` track-only; `test_transcript_inner_tick_streams.py` + `test_prompt_stack_tools_for_turn.py`. Merged pull/3766.

## 2026-07-07 scan (hygiene follow-up)

Source: open PR overlap check (#3785 REPL regression speedup — no harness overlap); ruff UP017/UP035/UP041/F401/F841 + vulture `--min-confidence 80` on `app/core/companion_harness/` + tests; #3413 follow-up — harness tests still seed/read MemDoc paths as string literals; UP017 `timezone.utc` in `test_greeting_loop_context.py`; F841 unused `batch` in `test_agentic_loop_output_queue.py`.

Open PRs checked: #3785 (`cursor/repl-regression-speedup-fe95`) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-74** ruff UP017 + #3413: `test_greeting_loop_context.py` — `datetime.UTC` + `TRANSCRIPT_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-f2d4` / pull/3786.
- [x] **HYGIENE-2026-75** #3413: `test_dreaming_batch_scripted_llm.py` — `CONTEXT_JSON_REL` + `TRANSCRIPT_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-f2d4` / pull/3786.
- [x] **HYGIENE-2026-76** #3413: `test_memory_store_scope.py` — canonical path constants for assertions + seed. Fixed in `cursor/agent-maintenance-tasks-f2d4` / pull/3786.
- [x] **HYGIENE-2026-77** #3413: `test_memory_store.py` — `TRANSCRIPT_JSONL_REL` for append/read. Fixed in `cursor/agent-maintenance-tasks-f2d4` / pull/3786.
- [x] **HYGIENE-2026-78** #3413: `test_experience_directives.py` — `CONTEXT_JSON_REL`. Fixed in `cursor/agent-maintenance-tasks-f2d4` / pull/3786.

## 2026-07-08 scan

Source: open PR overlap check (none open); ruff UP017/UP035/UP041/F401/F841 + vulture `--min-confidence 80` on `app/core/companion_harness/` + tests; #3413 follow-up — harness tests still seed/read MemDoc paths as string literals; F841 unused `batch` in `loop/test_agentic_loop_output_queue.py`.

Open PRs checked: none — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-79** ruff F841: `loop/test_agentic_loop_output_queue.py` — remove unused `batch` locals (3 sites). Fixed in `cursor/agent-maintenance-tasks-817f` / pull/3826.
- [x] **HYGIENE-2026-80** #3413: `test_memory_store_document_mapping.py` — roundtrip static paths from `memory_store_path_constants`. Fixed in `cursor/agent-maintenance-tasks-817f` / pull/3826.
- [x] **HYGIENE-2026-81** #3413: `test_turn_proactive_structured.py` — `TRANSCRIPT_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-817f` / pull/3826.
- [x] **HYGIENE-2026-82** #3413: `test_turn.py` — `CONTEXT_JSON_REL` + `TRANSCRIPT_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-817f` / pull/3826.
- [x] **HYGIENE-2026-83** #3413: `test_transcript_ai_private_hydrate.py` — `TRANSCRIPT_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-817f` / pull/3826.
- [x] **HYGIENE-2026-84** #3413: `test_living_sphere_runtime.py` — `CONTEXT_JSON_REL` + `LIVING_SPHERE_UPDATES_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-817f` / pull/3826.
- [x] **HYGIENE-2026-85** #3413: `test_implicit_sign_on_greeting_llm.py` — `CONTEXT_JSON_REL`. Fixed in `cursor/agent-maintenance-tasks-817f` / pull/3826.
- [x] **HYGIENE-2026-86** #3413: `test_harness_orchestration_scripted_llm.py` — `CONTEXT_JSON_REL`. Fixed in `cursor/agent-maintenance-tasks-817f` / pull/3826.
- [x] **HYGIENE-2026-87** #3413: `test_companion_drain_scripted_llm.py` — `CONTEXT_JSON_REL`. Fixed in `cursor/agent-maintenance-tasks-817f` / pull/3826.

## 2026-07-09 scan

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe touches `system_messages.py` + `test_prompt_builder.py` — defer F401 there); ruff UP017/UP035/UP041/F841 + vulture `--min-confidence 80` on `app/core/companion_harness/` + tests; #3413 follow-up — harness tests still seed/read MemDoc `.md` paths as string literals.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-88** #3413: `test_companion_user_feedback_tool.py` — `USER_MD_REL` + `MEMORY_MD_REL`. Fixed in `cursor/agent-maintenance-tasks-e2b6` / pull/3838.
- [x] **HYGIENE-2026-89** #3413: `test_memory_store.py` — `SOUL_MD_REL`. Fixed in `cursor/agent-maintenance-tasks-e2b6` / pull/3838.
- [x] **HYGIENE-2026-90** #3413: `test_resolve_client_time.py` — `USER_MD_REL`. Fixed in `cursor/agent-maintenance-tasks-e2b6` / pull/3838.
- [x] **HYGIENE-2026-91** #3413: `test_companion_record_user_profile_tool.py` — `USER_MD_REL` in write allowlist. Fixed in `cursor/agent-maintenance-tasks-e2b6` / pull/3838.

### Deferred (open PR overlap)

- **HYGIENE-2026-92** ruff F401: `system_messages.py` — unused `experience_profile_system_clause`, `experience_directives_system_clause`, `default_runtime_context_for_compose` (defer until #3834 lands).
- **HYGIENE-2026-93** ruff F401: `test_prompt_builder.py` — unused `PromptComposeTrigger` import (defer until #3834 lands).

## 2026-07-10 scan (stale code review)

Source: stale/legacy code review guided by `docs/imate/companion_harness/DESIGN.md`; vulture `--min-confidence 80` clean; 60% hits all false positives (Pydantic `model_config`, StrEnum values, invariant-check helpers, test/service refs). One superseded legacy function found kept alive only by its own test.

Open PRs checked: #3834 (`system_messages.py` recipe refactor — HYGIENE-2026-92/93 stay deferred, no overlap), #3837 (long-term user simulator — no overlap).

### Open tasks

- [x] **HYGIENE-2026-94** #3401: remove stale `append_tail_user_transcript_rows` (pre-#3401 tail-user transcript writer, no track/`inner_tick_kind`); superseded by `append_turn_track_tail_user_transcript_rows`; all production callers migrated, only its own test referenced it. Deleted function + orphaned `test_turn_tail_user.py::test_append_tail_user_transcript_rows_persists_each_user_message` and now-unused imports.

## 2026-07-10 scan (cron)

Source: open PR overlap check; ruff F401 (4 hits deferred in #3834 files); #3413 follow-up — harness tests still seed/read MemDoc `.md` paths as string literals in four files.

Open PRs checked: #3834 (`system_messages.py` + `test_prompt_builder.py` — HYGIENE-2026-92/93 stay deferred), #3837 (long-term user simulator — no overlap).

### Open tasks

- [x] **HYGIENE-2026-95** #3413: `tools/test_tools.py` — `USER_MD_REL` (+ `CHANNELS_MD_REL`, `LIFE_CURRENTS_MD_REL`). Fixed in `cursor/agent-maintenance-tasks-df99` / pull/3840.
- [x] **HYGIENE-2026-96** #3413: `memory/test_memory_pipeline_living_sphere.py` — canonical path constants in `_seed_store`. Fixed in `cursor/agent-maintenance-tasks-df99` / pull/3840.
- [x] **HYGIENE-2026-97** #3413: `memory/test_dreaming_consolidation.py` — canonical path constants for seed/read/assert. Fixed in `cursor/agent-maintenance-tasks-df99` / pull/3840.
- [x] **HYGIENE-2026-98** #3413: `runtime/test_dreaming_batch_scripted_llm.py` — remaining `IDENTITY`/`SOUL`/`USER`/`MEMORY`/`STYLE`/`COMPANIONSHIP` path literals. Fixed in `cursor/agent-maintenance-tasks-df99` / pull/3840.

## 2026-07-11 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe — HYGIENE-2026-92/93 stay deferred); ruff UP017/UP035/UP041/F841 + vulture `--min-confidence 80` clean except deferred F401; #3413 follow-up — harness tests still seed/read MemDoc `.md` paths as string literals in five files.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-99** #3413: `test_turn_proactive_structured.py` — `IDENTITY_MD_REL` + `SOUL_MD_REL` + `USER_MD_REL` + `MEMORY_MD_REL`. Fixed in `cursor/agent-maintenance-tasks-4a6a` / pull/3842.
- [x] **HYGIENE-2026-100** #3413: `test_turn.py` — `IDENTITY_MD_REL` + `SOUL_MD_REL` + `USER_MD_REL` + `MEMORY_MD_REL`. Fixed in `cursor/agent-maintenance-tasks-4a6a` / pull/3842.
- [x] **HYGIENE-2026-101** #3413: `test_turn_tracks.py` — seed tuple from canonical path constants. Fixed in `cursor/agent-maintenance-tasks-4a6a` / pull/3842.
- [x] **HYGIENE-2026-102** #3413: `test_implicit_sign_on_greeting_llm.py` — `IDENTITY_MD_REL` + `SOUL_MD_REL` + `USER_MD_REL` + `MEMORY_MD_REL`. Fixed in `cursor/agent-maintenance-tasks-4a6a` / pull/3842.
- [x] **HYGIENE-2026-103** #3413: `test_memory_store_scope.py` — property assertions + `ensure_minimal` read paths from canonical constants. Fixed in `cursor/agent-maintenance-tasks-4a6a` / pull/3842.

### Deferred (open PR overlap)

- **HYGIENE-2026-92** ruff F401: `system_messages.py` — unused imports (defer until #3834 lands).
- [x] **HYGIENE-2026-93** ruff F401: `test_prompt_builder.py` — unused `PromptComposeTrigger` import. Fixed in pull/3843.

## 2026-07-12 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe — HYGIENE-2026-92 stay deferred); ruff UP017/UP035/UP041/F841 + vulture `--min-confidence 80` clean except deferred F401; #3413 follow-up — harness tests still seed/read JSONL/state JSON paths as string literals.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-104** #3413: `test_memory_pipeline_living_sphere.py` — `LIVING_SPHERE_UPDATES_JSONL_REL` (2 sites). Fixed in `cursor/agent-maintenance-tasks-b253` / pull/3844.
- [x] **HYGIENE-2026-105** #3413: `test_living_sphere_curator.py` — `LIVING_SPHERE_UPDATES_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-b253` / pull/3844.
- [x] **HYGIENE-2026-106** #3413: `test_memory_pipeline_living_sphere.py` — `COMPANION_LIVING_SPHERE_CURATOR_JSON_REL` (2 sites). Fixed in `cursor/agent-maintenance-tasks-b253` / pull/3844.
- [x] **HYGIENE-2026-107** #3413: `test_transcript_compaction.py` — `COMPANION_CONTEXT_COMPACTION_STATE_JSON_REL`. Fixed in `cursor/agent-maintenance-tasks-b253` / pull/3844.

### Deferred (open PR overlap)

- **HYGIENE-2026-92** ruff F401: `system_messages.py` — unused imports (defer until #3834 lands).

## 2026-07-13 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe — HYGIENE-2026-92 stay deferred); ruff UP017/UP035/UP041/F841 + vulture `--min-confidence 80` clean except deferred F401; #3413 follow-up — harness tests still seed/read MemDoc `.md` paths as string literals.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-108** #3413: `test_living_sphere_runtime.py` — canonical path constants for seed tuples. Fixed in `cursor/agent-maintenance-tasks-b0ef` / pull/3846.
- [x] **HYGIENE-2026-109** #3413: `test_bootstrap_transcript_order.py` — `IDENTITY_MD_REL` + seed tuple. Fixed in `cursor/agent-maintenance-tasks-b0ef` / pull/3846.
- [x] **HYGIENE-2026-110** #3413: `test_ai_private_manifest_persist.py` — canonical path constants for seed loop. Fixed in `cursor/agent-maintenance-tasks-b0ef` / pull/3846.
- [x] **HYGIENE-2026-111** #3413: `companion_scripted_llm.py` — `LIFE_CURRENTS_MD_REL` + seed tuple. Fixed in `cursor/agent-maintenance-tasks-b0ef` / pull/3846.
- [x] **HYGIENE-2026-112** #3413: `test_models.py` — `CHANNELS_MD_REL` + `COMPANIONSHIP_MD_REL`. Fixed in `cursor/agent-maintenance-tasks-b0ef` / pull/3846.

### Deferred (open PR overlap)

- **HYGIENE-2026-92** ruff F401: `system_messages.py` — unused imports (defer until #3834 lands).

## 2026-07-14 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe — HYGIENE-2026-92 stay deferred); ruff UP017/UP035/UP041/F841 + vulture `--min-confidence 80` clean except deferred F401; #3413 follow-up — harness tests still seed/read MemDoc `.md` paths as string literals.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-113** #3413: `test_bootstrap.py` — canonical path constants for bootstrap write/read/seed tests. Fixed in `cursor/agent-maintenance-tasks-2ffe` / pull/3847.
- [x] **HYGIENE-2026-114** #3413: `test_inner_tick_autonomy_tool_names.py` — `LIFE_CURRENTS_MD_REL`. Fixed in `cursor/agent-maintenance-tasks-2ffe` / pull/3847.
- [x] **HYGIENE-2026-115** #3413: `test_memory_store_document_mapping.py` — `IDENTITY_MD_REL` in parse roundtrip. Fixed in `cursor/agent-maintenance-tasks-2ffe` / pull/3847.

### Deferred (open PR overlap)

- **HYGIENE-2026-92** ruff F401: `system_messages.py` — unused imports (defer until #3834 lands).

## 2026-07-15 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe — HYGIENE-2026-92 stay deferred); ruff UP017/UP035/UP041/F841 + vulture `--min-confidence 80` clean except deferred F401; #3413 follow-up — `ABOUT.md` still a string literal outside `memory_store_path_constants`.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-116** #3413: add `ABOUT_MD_REL` to `memory_store_path_constants`; wire `models.py` + `memory_store_scope.py`. Fixed in `cursor/agent-maintenance-tasks-9cf0`.
- [x] **HYGIENE-2026-117** #3413: `prompting/test_contextual.py` — `load_template_seed_text(ABOUT_MD_REL)`. Fixed in `cursor/agent-maintenance-tasks-9cf0`.
- [x] **HYGIENE-2026-118** #3413: `companion/test_models.py` — `load_template_seed_text(ABOUT_MD_REL)`. Fixed in `cursor/agent-maintenance-tasks-9cf0`.

### Deferred (open PR overlap)

- **HYGIENE-2026-92** ruff F401: `system_messages.py` — unused imports (defer until #3834 lands).

## 2026-07-16 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe — HYGIENE-2026-92 + #3413 MemDoc literals in `test_prompt_builder.py` / `test_system_messages.py` stay deferred); ruff UP017/UP035/UP041/F841 + vulture `--min-confidence 80` clean except deferred F401; #3413 follow-up — harness tests still hardcode `memory/daily/<date>.md` instead of `DEFAULT_MEMORY_STORE_SCOPE_PATHS.memory_daily_gist`.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-119** #3413: `tools/test_tools.py` — `memory_daily_gist("2099-01-01")` for daily seed path. Fixed in `cursor/agent-maintenance-tasks-9067` / pull/3849.
- [x] **HYGIENE-2026-120** #3413: `runtime/test_dreaming_batch_scripted_llm.py` — `memory_daily_gist(day_iso)` in `_seed_scope_due_for_one_shot_dreaming`. Fixed in `cursor/agent-maintenance-tasks-9067` / pull/3849.
- [x] **HYGIENE-2026-121** #3413: `memory/test_dreaming_consolidation.py` — `memory_daily_gist` for fixed test dates (`2026-01-02`, `2026-01-03`). Fixed in `cursor/agent-maintenance-tasks-9067` / pull/3849.

### Deferred (open PR overlap)

- **HYGIENE-2026-92** ruff F401: `system_messages.py` — unused imports (defer until #3834 lands).
- **HYGIENE-2026-122** #3413: `test_prompt_builder.py` — `IDENTITY_MD_REL` / `USER_MD_REL` / `LIFE_CURRENTS_MD_REL` (defer until #3834 lands).
- **HYGIENE-2026-123** #3413: `prompting/test_system_messages.py` — `ABOUT_MD_REL` + `LIFE_CURRENTS_MD_REL` assertions (defer until #3834 lands).
- **HYGIENE-2026-124** #3413: `companion/test_system_messages.py` — `SOUL_MD_REL` / `MEMORY_MD_REL` / `COMPANIONSHIP_MD_REL` (defer until #3834 lands).

## 2026-07-17 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe — HYGIENE-2026-92/122..124 stay deferred); ruff UP017/UP035/UP041/F841 + vulture `--min-confidence 80` clean except deferred F401; #3413 follow-up — prompt seed filenames still string literals in `memory_store_scope.py` and `bootstrap.py`.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-125** #3413: add `AXIOM_MD_REL`, `BOOTSTRAP_MD_REL`, `BOOTSTRAP_TELEGRAM_PROFILE_MD_REL`, `HARNESS_MD_REL`, `INTY_MD_REL`, `SAFETY_MD_REL`, `OUTPUT_FORMAT_IM_DM_MD_REL` to `memory_store_path_constants`. Fixed in `cursor/agent-maintenance-tasks-55f0` / pull/3850.
- [x] **HYGIENE-2026-126** #3413: `memory_store_scope.py` — `_PACKAGE_PROMPT_SEED_FILES` + `get_*_system_text` from canonical constants. Fixed in `cursor/agent-maintenance-tasks-55f0` / pull/3850.
- [x] **HYGIENE-2026-127** #3413: `bootstrap.py` — spec paths from `BOOTSTRAP_MD_REL` / `BOOTSTRAP_TELEGRAM_PROFILE_MD_REL`. Fixed in `cursor/agent-maintenance-tasks-55f0` / pull/3850.

### Deferred (open PR overlap)

- **HYGIENE-2026-92** ruff F401: `system_messages.py` — unused imports (defer until #3834 lands).
- **HYGIENE-2026-122** #3413: `test_prompt_builder.py` — `IDENTITY_MD_REL` / `USER_MD_REL` / `LIFE_CURRENTS_MD_REL` (defer until #3834 lands).
- **HYGIENE-2026-123** #3413: `prompting/test_system_messages.py` — `ABOUT_MD_REL` + `LIFE_CURRENTS_MD_REL` assertions (defer until #3834 lands).
- **HYGIENE-2026-124** #3413: `companion/test_system_messages.py` — `SOUL_MD_REL` / `MEMORY_MD_REL` / `COMPANIONSHIP_MD_REL` (defer until #3834 lands).

## 2026-07-18 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe — HYGIENE-2026-92/122..124 stay deferred); ruff UP017/UP035/UP041/F841 + vulture `--min-confidence 80` clean except deferred F401; #3413 follow-up — `models.py` still duplicates `HARNESS_MD` / `OUTPUT_FORMAT_IM_DM_MD` and inline `memory/daily/{day}.md`.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-128** #3413: `models.py` — `HARNESS_MD` → `HARNESS_MD_REL`. Fixed in `cursor/agent-maintenance-tasks-35b6` / pull/3851.
- [x] **HYGIENE-2026-129** #3413: `models.py` — `OUTPUT_FORMAT_IM_DM_MD` → `OUTPUT_FORMAT_IM_DM_MD_REL` (re-export alias for test imports). Fixed in `cursor/agent-maintenance-tasks-35b6` / pull/3851.
- [x] **HYGIENE-2026-130** #3413: `models.py` — `memory_daily_gist(day)` instead of `f"memory/daily/{day}.md"`. Fixed in `cursor/agent-maintenance-tasks-35b6` / pull/3851.

### Deferred (open PR overlap)

- **HYGIENE-2026-92** ruff F401: `system_messages.py` — unused imports (defer until #3834 lands).
- **HYGIENE-2026-122** #3413: `test_prompt_builder.py` — `IDENTITY_MD_REL` / `USER_MD_REL` / `LIFE_CURRENTS_MD_REL` (defer until #3834 lands).
- **HYGIENE-2026-123** #3413: `prompting/test_system_messages.py` — `ABOUT_MD_REL` + `LIFE_CURRENTS_MD_REL` assertions (defer until #3834 lands).
- **HYGIENE-2026-124** #3413: `companion/test_system_messages.py` — `SOUL_MD_REL` / `MEMORY_MD_REL` / `COMPANIONSHIP_MD_REL` (defer until #3834 lands).

## 2026-07-19 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe — HYGIENE-2026-92/122..124 stay deferred); ruff UP017/UP035/UP041/F841 + vulture `--min-confidence 80` clean except deferred F401; #3413 follow-up — `memory/daily/` path still duplicated in mapping, scope, and harness tests.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-131** #3413: add `memory_daily_gist_rel` to `memory_store_path_constants`; wire `memory_store_scope` + `memory_store_document_mapping`. Fixed in `cursor/agent-maintenance-tasks-1bb1` / pull/3852.
- [x] **HYGIENE-2026-132** #3413: `test_memory_store_document_mapping.py` — `memory_daily_gist_rel` for daily parse roundtrip. Fixed in `cursor/agent-maintenance-tasks-1bb1` / pull/3852.
- [x] **HYGIENE-2026-133** #3413: `test_memory_store_scope.py` — `memory_daily_gist_rel` in property assertion. Fixed in `cursor/agent-maintenance-tasks-1bb1` / pull/3852.
- [x] **HYGIENE-2026-134** #3413: `test_dreaming_consolidation.py` + `test_dreaming_batch_scripted_llm.py` — daily gist prefix via `MEMORY_DAILY_GIST_DIR_REL`. Fixed in `cursor/agent-maintenance-tasks-1bb1` / pull/3852.

### Deferred (open PR overlap)

- **HYGIENE-2026-92** ruff F401: `system_messages.py` — unused imports (defer until #3834 lands).
- **HYGIENE-2026-122** #3413: `test_prompt_builder.py` — `IDENTITY_MD_REL` / `USER_MD_REL` / `LIFE_CURRENTS_MD_REL` (defer until #3834 lands).
- **HYGIENE-2026-123** #3413: `prompting/test_system_messages.py` — `ABOUT_MD_REL` + `LIFE_CURRENTS_MD_REL` assertions (defer until #3834 lands).
- **HYGIENE-2026-124** #3413: `companion/test_system_messages.py` — `SOUL_MD_REL` / `MEMORY_MD_REL` / `COMPANIONSHIP_MD_REL` (defer until #3834 lands).

## 2026-07-20 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe — HYGIENE-2026-92/122..124 stay deferred); ruff UP017/UP035/UP041/F841 + vulture `--min-confidence 80` clean except deferred F401; #3413 follow-up — `.inty_v2` state JSON paths still use f-string fallback / string literals outside `memory_store_path_constants`.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-135** #3413: add `INTY_V2_DREAMING_STATE_JSON_REL`; wire `memory_store_scope` + `memory_store_document_mapping`. Fixed in `cursor/agent-maintenance-tasks-298d` / pull/3853.
- [x] **HYGIENE-2026-136** #3413: `test_memory_store_scope.py` — `INTY_V2_CONTEXT_COMPACTION_STATE_JSON_REL` for `.inty_v2` prefix. Fixed in `cursor/agent-maintenance-tasks-298d` / pull/3853.
- [x] **HYGIENE-2026-137** #3413: `test_memory_store_document_mapping.py` — roundtrip `INTY_V2_*` + companion state JSON paths. Fixed in `cursor/agent-maintenance-tasks-298d` / pull/3853.

### Deferred (open PR overlap)

- **HYGIENE-2026-92** ruff F401: `system_messages.py` — unused imports (defer until #3834 lands).
- **HYGIENE-2026-122** #3413: `test_prompt_builder.py` — `IDENTITY_MD_REL` / `USER_MD_REL` / `LIFE_CURRENTS_MD_REL` (defer until #3834 lands).
- **HYGIENE-2026-123** #3413: `prompting/test_system_messages.py` — `ABOUT_MD_REL` + `LIFE_CURRENTS_MD_REL` assertions (defer until #3834 lands).
- **HYGIENE-2026-124** #3413: `companion/test_system_messages.py` — `SOUL_MD_REL` / `MEMORY_MD_REL` / `COMPANIONSHIP_MD_REL` (defer until #3834 lands).

## 2026-07-21 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe — HYGIENE-2026-92/122..124 stay deferred); ruff UP017/UP035/UP041/F841 + vulture `--min-confidence 80` clean except deferred F401; #3413 follow-up — scope-path property tests and document-mapping roundtrip still omit mapped rel paths.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-138** #3413: `test_dreaming_consolidation.py` — legacy flat daily path via named constant. Fixed in `cursor/agent-maintenance-tasks-95db` / pull/3854.
- [x] **HYGIENE-2026-139** #3413: `test_memory_store_scope.py` — `significance_perception_md` + `transcript_inner_tick` property assertions. Fixed in `cursor/agent-maintenance-tasks-95db` / pull/3854.
- [x] **HYGIENE-2026-140** #3413: `test_memory_store_document_mapping.py` — roundtrip remaining `_REL_TO_KIND` static paths. Fixed in `cursor/agent-maintenance-tasks-95db` / pull/3854.

### Deferred (open PR overlap)

- **HYGIENE-2026-92** ruff F401: `system_messages.py` — unused imports (defer until #3834 lands).
- **HYGIENE-2026-122** #3413: `test_prompt_builder.py` — `IDENTITY_MD_REL` / `USER_MD_REL` / `LIFE_CURRENTS_MD_REL` (defer until #3834 lands).
- **HYGIENE-2026-123** #3413: `prompting/test_system_messages.py` — `ABOUT_MD_REL` + `LIFE_CURRENTS_MD_REL` assertions (defer until #3834 lands).
- **HYGIENE-2026-124** #3413: `companion/test_system_messages.py` — `SOUL_MD_REL` / `MEMORY_MD_REL` / `COMPANIONSHIP_MD_REL` (defer until #3834 lands).

## 2026-07-22 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe — HYGIENE-2026-92/122..124 stay deferred); ruff UP017/UP035/UP041/F841 + vulture `--min-confidence 80` clean except deferred F401; #3413 follow-up — `retrieval.py` still hardcodes `CHAT_HISTORY.md`; harness tests still import path constants via module re-exports.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-141** #3413: add `CHAT_HISTORY_MD_REL` to `memory_store_path_constants`; wire `retrieval.py`. Fixed in `cursor/agent-maintenance-tasks-ae51` / pull/3855.
- [x] **HYGIENE-2026-142** #3413: `test_bootstrap_complete_not_blocked_without_profile.py` — `USER_MD_REL` from `memory_store_path_constants`. Fixed in `cursor/agent-maintenance-tasks-ae51` / pull/3855.
- [x] **HYGIENE-2026-143** #3413: `test_companion_user_feedback_tool.py` — `COMPANION_USER_FEEDBACK_JSONL_REL` from constants (drop re-export). Fixed in `cursor/agent-maintenance-tasks-ae51` / pull/3855.
- [x] **HYGIENE-2026-144** #3413: `test_companion_record_user_profile_tool.py` — `USER_MD_REL` from constants. Fixed in `cursor/agent-maintenance-tasks-ae51` / pull/3855.

### Deferred (open PR overlap)

- **HYGIENE-2026-92** ruff F401: `system_messages.py` — unused imports (defer until #3834 lands).
- **HYGIENE-2026-122** #3413: `test_prompt_builder.py` — `IDENTITY_MD_REL` / `USER_MD_REL` / `LIFE_CURRENTS_MD_REL` (defer until #3834 lands).
- **HYGIENE-2026-123** #3413: `prompting/test_system_messages.py` — `ABOUT_MD_REL` + `LIFE_CURRENTS_MD_REL` assertions (defer until #3834 lands).
- **HYGIENE-2026-124** #3413: `companion/test_system_messages.py` — `SOUL_MD_REL` / `MEMORY_MD_REL` / `COMPANIONSHIP_MD_REL` (defer until #3834 lands).

## 2026-07-23 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe — HYGIENE-2026-92/122..124 stay deferred); ruff UP017/UP035/UP041/F841 + vulture `--min-confidence 80` clean except deferred F401; follow-up — `retrieval.py` `CHAT_HISTORY_MD_REL` window spec untested; doctrine prompt getters untested; UP041 `asyncio.TimeoutError` in two companion test modules.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-145** ruff UP041: replace `asyncio.TimeoutError` with builtin `TimeoutError` in `test_implicit_sign_on_greeting_llm.py` and `test_companion_llm_client.py`. Fixed in `cursor/agent-maintenance-tasks-3cdf` / pull/3856.
- [x] **HYGIENE-2026-146** `memory/test_retrieval.py` — `select_slices_for_turn` uses `CHAT_HISTORY_MD_REL` as `transcript_window_spec`. Fixed in `cursor/agent-maintenance-tasks-3cdf` / pull/3856.
- [x] **HYGIENE-2026-147** `memory/test_memory_store_scope.py` — smoke `get_imate_axiom_system_text` / `get_inty_facts_system_text` / `get_safety_system_text`. Fixed in `cursor/agent-maintenance-tasks-3cdf` / pull/3856.

### Deferred (open PR overlap)

- **HYGIENE-2026-92** ruff F401: `system_messages.py` — unused imports (defer until #3834 lands).
- **HYGIENE-2026-122** #3413: `test_prompt_builder.py` — `IDENTITY_MD_REL` / `USER_MD_REL` / `LIFE_CURRENTS_MD_REL` (defer until #3834 lands).
- **HYGIENE-2026-123** #3413: `prompting/test_system_messages.py` — `ABOUT_MD_REL` + `LIFE_CURRENTS_MD_REL` assertions (defer until #3834 lands).
- **HYGIENE-2026-124** #3413: `companion/test_system_messages.py` — `SOUL_MD_REL` / `MEMORY_MD_REL` / `COMPANIONSHIP_MD_REL` (defer until #3834 lands).

## 2026-07-24 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe — HYGIENE-2026-92/122..124 stay deferred); ruff UP017/UP035/UP041/F841 + vulture `--min-confidence 80` clean except deferred F401; #3413 follow-up — package prompt seeds and bootstrap spec loaders lack canonical-path smoke coverage in tests outside #3834 scope.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-148** `memory/test_memory_store_scope.py` — smoke `load_template_seed_text` for all `_PACKAGE_PROMPT_SEED_FILES` rel constants. Fixed in `cursor/agent-maintenance-tasks-2d5c` / pull/3857.
- [x] **HYGIENE-2026-149** `companion/test_models.py` — `load_prompt_bundle` harness slice matches `HARNESS_MD_REL` seed. Fixed in `cursor/agent-maintenance-tasks-2d5c` / pull/3857.
- [x] **HYGIENE-2026-150** `companion/test_bootstrap.py` — `load_bootstrap_spec_text` / telegram slice align with `BOOTSTRAP_MD_REL` / `BOOTSTRAP_TELEGRAM_PROFILE_MD_REL`; wire telegram profile into `_PACKAGE_PROMPT_SEED_FILES`. Fixed in `cursor/agent-maintenance-tasks-2d5c` / pull/3857.

### Deferred (open PR overlap)

- **HYGIENE-2026-92** ruff F401: `system_messages.py` — unused imports (defer until #3834 lands).
- **HYGIENE-2026-122** #3413: `test_prompt_builder.py` — `IDENTITY_MD_REL` / `USER_MD_REL` / `LIFE_CURRENTS_MD_REL` (defer until #3834 lands).
- **HYGIENE-2026-123** #3413: `prompting/test_system_messages.py` — `ABOUT_MD_REL` + `LIFE_CURRENTS_MD_REL` assertions (defer until #3834 lands).
- **HYGIENE-2026-124** #3413: `companion/test_system_messages.py` — `SOUL_MD_REL` / `MEMORY_MD_REL` / `COMPANIONSHIP_MD_REL` (defer until #3834 lands).

## 2026-07-25 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe — HYGIENE-2026-92/122..124 stay deferred); ruff UP017/UP035/UP041/F841 + vulture `--min-confidence 80` clean except deferred F401; follow-up — `load_prompt_bundle` core MemDoc reads and retrieval slice selection lack canonical-path smoke coverage outside #3834 scope.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-151** `companion/test_models.py` — smoke `load_prompt_bundle` reads `SOUL_MD_REL` / `MEMORY_MD_REL` / `STYLE_MD_REL` / `IDENTITY_MD_REL` / `USER_MD_REL` from store. Fixed in `cursor/agent-maintenance-tasks-f010` / pull/3858.
- [x] **HYGIENE-2026-152** `memory/test_retrieval.py` — parametrize `select_slices_for_turn` across USER_CHAT + inner-tick tracks. Fixed in `cursor/agent-maintenance-tasks-f010` / pull/3858.
- [x] **HYGIENE-2026-153** `memory/test_memory_store_scope.py` — assert `memory_daily_gist_rel` uses `MEMORY_DAILY_GIST_DIR_REL` prefix. Fixed in `cursor/agent-maintenance-tasks-f010` / pull/3858.

### Deferred (open PR overlap)

- **HYGIENE-2026-92** ruff F401: `system_messages.py` — unused imports (defer until #3834 lands).
- **HYGIENE-2026-122** #3413: `test_prompt_builder.py` — `IDENTITY_MD_REL` / `USER_MD_REL` / `LIFE_CURRENTS_MD_REL` (defer until #3834 lands).
- **HYGIENE-2026-123** #3413: `prompting/test_system_messages.py` — `ABOUT_MD_REL` + `LIFE_CURRENTS_MD_REL` assertions (defer until #3834 lands).
- **HYGIENE-2026-124** #3413: `companion/test_system_messages.py` — `SOUL_MD_REL` / `MEMORY_MD_REL` / `COMPANIONSHIP_MD_REL` (defer until #3834 lands).

## 2026-07-26 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe — HYGIENE-2026-92/122..124 stay deferred); ruff UP017/UP035/UP041/F841 + vulture `--min-confidence 80` clean except deferred F401; follow-up — `load_prompt_bundle` optional MemDoc reads and `SLOT_RANK` keys lack canonical-path smoke coverage outside #3834 scope.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-154** `companion/test_models.py` — smoke `load_prompt_bundle` loads `TOOLS_MD_REL` package template. Fixed in `cursor/agent-maintenance-tasks-2571` / pull/3859.
- [x] **HYGIENE-2026-155** `companion/test_models.py` — smoke `load_prompt_bundle` loads `SIGNIFICANCE_PERCEPTION_MD_REL` package template. Fixed in `cursor/agent-maintenance-tasks-2571` / pull/3859.
- [x] **HYGIENE-2026-156** `prompting/test_projection_stubs.py` — assert `SLOT_RANK` keys are canonical `*_MD_REL` constants. Fixed in `cursor/agent-maintenance-tasks-2571` / pull/3859.

## 2026-07-27 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe — overlapping files but disjoint hunks; deferred #3413/F401 follow-up unblocked); ruff F401 (3 hits in `system_messages.py`); vulture `--min-confidence 80` clean.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no direct task overlap.

### Claimed (in progress — `cursor/agent-maintenance-tasks-2e8a`)

- [x] **HYGIENE-2026-92** ruff F401: remove unused imports in `prompting/system_messages.py`. Fixed in `cursor/agent-maintenance-tasks-2e8a` / pull/3860.
- [x] **HYGIENE-2026-122** #3413: `test_prompt_builder.py` — `IDENTITY_MD_REL` / `USER_MD_REL` / `LIFE_CURRENTS_MD_REL`. Fixed in `cursor/agent-maintenance-tasks-2e8a` / pull/3860.
- [x] **HYGIENE-2026-123** #3413: `prompting/test_system_messages.py` — `ABOUT_MD_REL` + `LIFE_CURRENTS_MD_REL`. Fixed in `cursor/agent-maintenance-tasks-2e8a` / pull/3860.
- [x] **HYGIENE-2026-124** #3413: `companion/test_system_messages.py` — `SOUL_MD_REL` / `MEMORY_MD_REL` / `COMPANIONSHIP_MD_REL`. Fixed in `cursor/agent-maintenance-tasks-2e8a` / pull/3860.

## 2026-07-28 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe, #3837 long-term user simulator — no overlap); ruff UP017/UP035/UP041/F401/F841 + vulture `--min-confidence 80` clean; follow-up — `load_prompt_bundle` optional MemDoc reads and tool write allowlists lack canonical-path smoke coverage.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Claimed (in progress — `cursor/agent-maintenance-tasks-ef73`)

- [x] **HYGIENE-2026-157** `companion/test_models.py` — smoke `load_prompt_bundle` reads `TECHNO_CORE_MD_REL` / `LIVING_SPHERE_MD_REL` from store. Fixed in `cursor/agent-maintenance-tasks-ef73` / pull/3861.
- [x] **HYGIENE-2026-158** `companion/test_models.py` — smoke `load_prompt_bundle` loads `OUTPUT_FORMAT_IM_DM_MD_REL` package template. Fixed in `cursor/agent-maintenance-tasks-ef73` / pull/3861.
- [x] **HYGIENE-2026-159** `tools/test_companion_tool_definitions.py` — assert `MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST*` ⊆ canonical `*_MD_REL` constants. Fixed in `cursor/agent-maintenance-tasks-ef73` / pull/3861.

## 2026-07-29 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe, #3837 long-term user simulator — no overlap); ruff UP017/UP035/UP041/F401/F841 + vulture `--min-confidence 80` clean; follow-up — `MemoryStoreScopePaths` missing mapped MemDoc/JSONL accessors; AUTONOMY write allowlist lacks explicit canonical-path assertion.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Claimed (in progress — `cursor/agent-maintenance-tasks-a290`)

- [x] **HYGIENE-2026-160** #3413: `memory_store_scope.py` — add `life_currents_md` property; wire `test_memory_store_scope.py`. Fixed in `cursor/agent-maintenance-tasks-a290` / pull/3862.
- [x] **HYGIENE-2026-161** #3413: `memory_store_scope.py` — add `ai_private_md` + `ai_private_jsonl` properties; wire `test_memory_store_scope.py`. Fixed in `cursor/agent-maintenance-tasks-a290` / pull/3862.
- [x] **HYGIENE-2026-162** #3413: `memory_store_scope.py` — add `tool_background_jsonl` property; wire `test_memory_store_scope.py`. Fixed in `cursor/agent-maintenance-tasks-a290` / pull/3862.
- [x] **HYGIENE-2026-163** `tools/test_companion_tool_definitions.py` — assert `MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY == {LIFE_CURRENTS_MD_REL}`. Fixed in `cursor/agent-maintenance-tasks-a290` / pull/3862.

## 2026-07-30 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe, #3837 long-term user simulator — no overlap); ruff UP017/UP035/UP041/F401/F841 + vulture `--min-confidence 80` clean; follow-up — `MemoryStoreScopePaths` missing event JSONL / feedback / image-index accessors; USER_CHAT + bootstrap write allowlists lack explicit canonical-path assertions.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Claimed (in progress — `cursor/agent-maintenance-tasks-7836`)

- [x] **HYGIENE-2026-164** #3413: `memory_store_scope.py` — add `techno_core_events_jsonl`, `living_sphere_updates_jsonl`, `companion_runtime_events_jsonl`, `companion_user_feedback_jsonl`, `generated_images_index_jsonl`, `chat_history_md` properties. Fixed in `cursor/agent-maintenance-tasks-7836` / pull/3863.
- [x] **HYGIENE-2026-165** #3413: `test_memory_store_scope.py` — property assertions for HYGIENE-2026-164 accessors. Fixed in `cursor/agent-maintenance-tasks-7836` / pull/3863.
- [x] **HYGIENE-2026-166** `tools/test_companion_tool_definitions.py` — explicit frozenset assertions for `MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST` and `MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP`. Fixed in `cursor/agent-maintenance-tasks-7836` / pull/3863.

## 2026-07-31 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe, #3837 long-term user simulator — no overlap); ruff UP017/UP035/UP041/F401/F841 + vulture `--min-confidence 80` clean; follow-up — `user_md_identity.py` hardcodes template filename; `USER_FEEDBACK_JSONL_REL` alias redundant; retrieval test does not tie window spec to `MemoryStoreScopePaths`.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Claimed (in progress — `cursor/agent-maintenance-tasks-6ab2`)

- [x] **HYGIENE-2026-167** #3413: `user_md_identity.py` — `load_user_md_template_text` via `load_template_seed_text(USER_MD_REL)` (drop `_USER_TEMPLATE_PATH` hardcode). Fixed in `cursor/agent-maintenance-tasks-6ab2` / pull/3864.
- [x] **HYGIENE-2026-168** `memory/test_retrieval.py` — assert `transcript_window_spec` matches `DEFAULT_MEMORY_STORE_SCOPE_PATHS.chat_history_md`. Fixed in `cursor/agent-maintenance-tasks-6ab2` / pull/3864.
- [x] **HYGIENE-2026-169** #3413: `companion_user_feedback.py` — drop `USER_FEEDBACK_JSONL_REL` alias; callers use `COMPANION_USER_FEEDBACK_JSONL_REL`. Fixed in `cursor/agent-maintenance-tasks-6ab2` / pull/3864.

## 2026-08-01 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe, #3837 long-term user simulator — no overlap); ruff UP017/UP035/UP041/F401/F841 + vulture `--min-confidence 80` clean; follow-up — `ABOUT_MD_REL` lacks `MemoryStoreScopePaths` accessor; harness tests still import `OUTPUT_FORMAT_IM_DM_MD` models alias; `load_user_md_template_text` lacks canonical-path smoke assertion.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Claimed (in progress — `cursor/agent-maintenance-tasks-95cc`)

- [x] **HYGIENE-2026-170** #3413: `memory_store_scope.py` — add `about_md` property; wire `test_memory_store_scope.py`. Fixed in `cursor/agent-maintenance-tasks-95cc` / pull/3865.
- [x] **HYGIENE-2026-171** `memory/test_user_md_identity.py` — assert `load_user_md_template_text()` matches `load_template_seed_text(USER_MD_REL)`. Fixed in `cursor/agent-maintenance-tasks-95cc` / pull/3865.
- [x] **HYGIENE-2026-172** #3413: `prompting/test_system_messages.py` — `OUTPUT_FORMAT_IM_DM_MD_REL` from constants (drop models re-export import). Fixed in `cursor/agent-maintenance-tasks-95cc` / pull/3865.

## 2026-08-02 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe, #3837 long-term user simulator — no overlap); ruff UP017/UP035/UP041/F401/F841 + vulture `--min-confidence 80` clean; follow-up — `bootstrap.py` still reads prompt seeds via local `Path`; package prompt seeds lack `MemoryStoreScopePaths` accessors.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Claimed (in progress — `cursor/agent-maintenance-tasks-a8f2`)

- [x] **HYGIENE-2026-173** #3413: `bootstrap.py` — `load_bootstrap_spec_text` / `load_bootstrap_telegram_profile_slice_text` via `load_template_seed_text` (drop `_BOOTSTRAP_SPEC_PATH` hardcodes). Fixed in `cursor/agent-maintenance-tasks-a8f2` / pull/3866.
- [x] **HYGIENE-2026-174** #3413: `memory_store_scope.py` — add `harness_md`, `bootstrap_md`, `bootstrap_telegram_profile_md`, `output_format_im_dm_md`, `axiom_md`, `inty_md`, `safety_md` properties; wire `test_memory_store_scope.py`. Fixed in `cursor/agent-maintenance-tasks-a8f2` / pull/3866.
- [x] **HYGIENE-2026-175** `memory/test_memory_store_scope.py` — assert `_PACKAGE_PROMPT_SEED_FILES` matches `MemoryStoreScopePaths` prompt-seed accessor rel paths. Fixed in `cursor/agent-maintenance-tasks-a8f2` / pull/3866.

## 2026-08-03 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe, #3837 long-term user simulator — no overlap); ruff UP017/UP035/UP041/F401/F841 + vulture `--min-confidence 80` clean; follow-up — `_CORE_COMPANION_TEMPLATE_REL_PATHS` / `_REQUIRED_FILES_ATTR` lack accessor parity tests; `BOOTSTRAP_WRITABLE_REL_PATHS` lacks `MemoryStoreScopePaths` smoke assertion.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Claimed (in progress — `cursor/agent-maintenance-tasks-1db3`)

- [x] **HYGIENE-2026-176** `memory/test_memory_store_scope.py` — assert `_CORE_COMPANION_TEMPLATE_REL_PATHS` matches `MemoryStoreScopePaths` core template accessor rel paths. Fixed in `cursor/agent-maintenance-tasks-1db3` / pull/3867.
- [x] **HYGIENE-2026-177** `memory/test_memory_store_scope.py` — assert `_REQUIRED_FILES_ATTR` matches `MemoryStoreScopePaths` required-file accessor rel paths. Fixed in `cursor/agent-maintenance-tasks-1db3` / pull/3867.
- [x] **HYGIENE-2026-178** `companion/test_bootstrap.py` — assert `BOOTSTRAP_WRITABLE_REL_PATHS` matches `DEFAULT_MEMORY_STORE_SCOPE_PATHS` bootstrap write accessors. Fixed in `cursor/agent-maintenance-tasks-1db3` / pull/3867.

## 2026-08-04 scan (cron)

Source: open PR overlap check (#3834 Phase 2 TrackSystemRecipe, #3837 long-term user simulator — no overlap); ruff UP017/UP035/UP041/F401/F841 + vulture `--min-confidence 80` clean; follow-up — `lifecycle_invariants` awake append JSONL constants and doctrine prompt getters lack `MemoryStoreScopePaths` smoke assertions; `_REL_TO_KIND` mapped paths lack accessor parity test.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`) — no overlap with tasks below.

### Claimed (in progress — `cursor/agent-maintenance-tasks-d3c7`)

- [x] **HYGIENE-2026-179** `companion/test_lifecycle_invariants.py` — assert `AWAKE_TURN_ALLOWED_APPEND_JSONL` + `AWAKE_TURN_TOOL_BACKGROUND_LOG_JSONL` match `DEFAULT_MEMORY_STORE_SCOPE_PATHS` transcript/tool-background accessors. Fixed in `cursor/agent-maintenance-tasks-d3c7` / pull/3868.
- [x] **HYGIENE-2026-180** `memory/test_memory_store_scope.py` — assert doctrine getters (`get_imate_axiom_system_text` / `get_inty_facts_system_text` / `get_safety_system_text`) match `load_template_seed_text` for canonical `*_MD_REL` paths. Fixed in `cursor/agent-maintenance-tasks-d3c7` / pull/3868.
- [x] **HYGIENE-2026-181** `memory/test_memory_store_document_mapping.py` — assert `_REL_TO_KIND` mapped static paths match `MemoryStoreScopePaths` accessor rel paths. Fixed in `cursor/agent-maintenance-tasks-d3c7` / pull/3868.

## 2026-08-05 scan (cron)

Source: open PR overlap check (#3869–#3880 HYGIENE-2026-182..234 scope-path accessor wave — no overlap); ruff UP017/UP035/UP041/F401/F841 + vulture `--min-confidence 80` clean; follow-up — harness tests still seed/read MemDoc paths via `*_REL` constants instead of `MemoryStoreScopePaths` accessors.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`), #3869–#3880 (HYGIENE-2026-182..234) — no overlap with tasks below.

### Claimed (in progress — `cursor/agent-maintenance-tasks-40e8`)

- [x] **HYGIENE-2026-235** `companion/test_transcript_inner_tick_streams.py` — transcript rel params + seed/read via scope accessors. Fixed in `cursor/agent-maintenance-tasks-40e8` / pull/3881.
- [x] **HYGIENE-2026-236** `memory/test_living_sphere_curator.py` — `living_sphere_md` / `living_sphere_updates_jsonl` accessors. Fixed in `cursor/agent-maintenance-tasks-40e8` / pull/3881.
- [x] **HYGIENE-2026-237** `memory/test_resolve_client_time.py` — `user_md` accessor. Fixed in `cursor/agent-maintenance-tasks-40e8` / pull/3881.
- [x] **HYGIENE-2026-238** `tools/test_read_web_page_tool.py` — `memory_md` accessor. Fixed in `cursor/agent-maintenance-tasks-40e8` / pull/3881.
- [x] **HYGIENE-2026-239** `companion/test_turn.py` — workspace seed + transcript/context reads via scope accessors. Fixed in `cursor/agent-maintenance-tasks-40e8` / pull/3881.

## 2026-08-17 scan (cron)

Source: open PR overlap check (#3869–#3881 HYGIENE-2026-182..239 scope-path accessor wave — no overlap); ruff UP017/UP035/UP041/F401/F841 + vulture `--min-confidence 80` clean; follow-up — harness tests still seed/read MemDoc paths via `*_REL` constants instead of `MemoryStoreScopePaths` accessors; stale issue audit doc remains.

Open PRs checked: #3834 (`cursor/phase-2-tracksystemrecipe-b95a`), #3837 (`cursor/long-term-user-simulator-4deb`), #3869–#3881 (HYGIENE-2026-182..239), #3882 (stale compose-context bridge) — no overlap with tasks below.

### Claimed (in progress — `cursor/agent-maintenance-tasks-8dd2`)

- [x] **HYGIENE-2026-240** `companion/test_turn_tracks.py` — context + workspace seed via scope accessors. Fixed in `cursor/agent-maintenance-tasks-8dd2` / pull/3883.
- [x] **HYGIENE-2026-241** `companion/test_turn_proactive_structured.py` — workspace seed + transcript read via scope accessors. Fixed in `cursor/agent-maintenance-tasks-8dd2` / pull/3883.
- [x] **HYGIENE-2026-242** `companion/test_proactive_chat.py` — transcript seed/append via `transcript` accessor. Fixed in `cursor/agent-maintenance-tasks-8dd2` / pull/3883.
- [x] **HYGIENE-2026-243** `companion/test_inner_tick_schedule.py` — transcript + `context_json` via scope accessors. Fixed in `cursor/agent-maintenance-tasks-8dd2` / pull/3883.
- [x] **HYGIENE-2026-244** `companion/test_implicit_sign_on_greeting_llm.py` — workspace seed via scope accessors. Fixed in `cursor/agent-maintenance-tasks-8dd2` / pull/3883.
- [x] **HYGIENE-2026-245** Remove stale `.agents/maintenance/COMPANION_HARNESS_ISSUE_AUDIT_2026-07-09.md`. Fixed in `cursor/agent-maintenance-tasks-8dd2` / pull/3883.
