# Companion Harness Hygiene

Maintenance agents fix **one TODO per commit** when possible. Mark `claimed` with branch name before implementation.

## 2026-06-22 scan

Source: open PR overlap check (#3611 #3400 rename, #3620 #3375 ai_private.md reader); ruff UP017/UP035/UP041 + vulture `--min-confidence 80` — clean.

Open PRs checked: #3611 (INNER_TICK_MONOLOG rename #3400), #3620 (dead ai_private.md reader #3375) — no overlap with tasks below.

### Open tasks

- [x] **HYGIENE-2026-07** #3551: Dreaming batch LangSmith parent — `record_dreaming_batch_observability` on failure paths (`DreamingTranscriptBoundaryMismatchError` etc.). Fixed in `cursor/agent-maintenance-tasks-b0b1` / pull/3621.
- [x] **HYGIENE-2026-08** #3413: Export module-level `Final` MemDoc path constants in `memory_store_path_constants.py`; migrate ad-hoc `_USER_MD_REL` / `_MEMORY_REL` in `read_web_page.py`, `client_time_from_memory_store.py`, `companion_tool_runtime.py`, `image_gate.py`. Fixed in `cursor/agent-maintenance-tasks-b0b1` / pull/3621.
- [x] **HYGIENE-2026-09** #3413: Wire `memory_store_document_mapping._REL_TO_KIND` keys and `needs_startup_profile_inquiry` to canonical path constants. Fixed in `cursor/agent-maintenance-tasks-b0b1` / pull/3621.

### Completed (2026-06-20)

- [x] **HYGIENE-2026-01** … **HYGIENE-2026-06** — see git history on `main`.
