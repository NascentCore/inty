# Fix Violations of Python Style Guides

Maintenance agents fix **one TODO per commit** when possible. Mark `claimed` with branch name before implementation.

## 2026-06-17 scan

### Open violations

- [x] **STYLE-2026-01** Google 2.4 / hygiene: companion-harness scope **unused imports** (`ruff F401` on `manager.py`, `agentic_loop.py`, `output_queue.py`, `inner_tick_fire.py`, `inner_tick_poll.py`). Fixed in `cursor/agent-maintenance-tasks-826b`.
- [x] **STYLE-2026-02** Google 2.4 "Exceptions": `app/core/companion_harness/agentic_companion/companion.py` worker loop swallows `drain_once` failures with `except Exception: pass`. Log with `logger.exception` and continue polling. Fixed in `cursor/agent-maintenance-tasks-826b`.
- [x] **STYLE-2026-03** Google 2.4 "Exceptions": `backend/ops/schemas/festival_memory.py` `_validate_iana_timezone` catches broad `Exception`; narrow to `ZoneInfoNotFoundError`. Fixed in `cursor/agent-maintenance-tasks-826b`.
- [x] **STYLE-2026-04** Google 2.4 "Exceptions": `backend/ops/weixin_channel/weixin_qr_flow.py` QR status poll loop silently continues on broad `Exception`. Log unexpected failures before retry. Fixed in `cursor/agent-maintenance-tasks-826b`.

## 2026-06-18 scan

### Open violations

- [x] **STYLE-2026-05** Google 2.4 / hygiene: backend/ops **unused imports** (`ruff F401` on `agent_channel.py`, `evaluation.py`, `telegram_demo/persistence.py`, `telegram_demo/session_store.py`, `weixin_channel/session.py`). Fixed in `cursor/agent-maintenance-tasks-6417`.
- [x] **STYLE-2026-06** Google 2.4 "Exceptions": `backend/ops/api/v1/evaluation.py` WebSocket monitor loop breaks on broad `Exception` without logging. Narrow to `WebSocketDisconnect`; log unexpected failures. Fixed in `cursor/agent-maintenance-tasks-6417`.
- [x] **STYLE-2026-07** Google 2.4 / hygiene: `backend/ops/api/v1/evaluation.py` uses `is_public == True` (`ruff E712`). Use truth check on column. Fixed in `cursor/agent-maintenance-tasks-6417`.

## 2026-06-19 scan

### Open violations

- [x] **STYLE-2026-08** PY_STYLE_RULES logging: `backend/ops/main.py` formats exceptions into log messages (`f"...{str(e)}"`). Use structured loguru placeholders + `exc_info` / `logger.exception`. Fixed in `cursor/agent-maintenance-tasks-1924`.
- [x] **STYLE-2026-09** Google 2.4 "Exceptions": `backend/ops/weixin_channel/weixin_qr_flow.py` QR fetch (`except Exception` ~L61) sets `self.error` without logging. Log with `logger.exception` before failure return. Fixed in `cursor/agent-maintenance-tasks-1924`.
- [x] **STYLE-2026-10** PY_STYLE_RULES + B904: `backend/ops/api/v1/evaluation.py` session list/create/start/detail handlers use f-string error logs and bare `raise HTTPException`. Structured logging; `raise ... from e` / `from None`. Fixed in `cursor/agent-maintenance-tasks-1924`.
- [x] **STYLE-2026-11** PY_STYLE_RULES + B904: remaining `backend/ops/api/v1/evaluation.py` handlers (~50 f-string logs, ~60 bare `raise HTTPException`). Batch by router section (results/cancel, questions, agents, analytics). Fixed in `cursor/agent-maintenance-tasks-64e4`.
