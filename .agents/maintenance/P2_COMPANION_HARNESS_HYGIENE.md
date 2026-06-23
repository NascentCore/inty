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

## 2026-06-23 scan

Source: issue audit `hygiene_defer` lane; ruff UP017/UP035/UP041 + vulture `--min-confidence 80` clean on `app/core/companion_harness/`.

Open PRs checked: #3611 (#3400 monolog rename), #3620 (#3375 ai_private.md reader), #3621 (HYGIENE-2026-07..09 #3551/#3413), #3622 (issue audit), #3623 (#3417 prompt_slices) — no overlap.

### Open tasks

- [ ] **HYGIENE-2026-10** #3553: hoist `langsmith_slice` onto `CompanionTurnDeps`; turn + tool_background share `deps.langsmith_slice`. `claimed` `cursor/agent-maintenance-tasks-c4bb`.
- [ ] **HYGIENE-2026-11** #3552: atomic `MemoryStore.append_jsonl_record` (store lock) for concurrent user-feedback appends. `claimed` `cursor/agent-maintenance-tasks-c4bb`.
- [ ] **HYGIENE-2026-12** #3550: Postgres `pg_try_advisory_lock` per scope in `run_dreaming_batch_if_due`; skip + observability on contention. `claimed` `cursor/agent-maintenance-tasks-c4bb`.
