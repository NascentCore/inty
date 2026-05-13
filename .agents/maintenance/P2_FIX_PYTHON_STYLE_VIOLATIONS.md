# Fix Violations of Python Style Guides

This file tracks discovered violations of Google's Python Style Guide so
maintenance agents can fix the highest-impact item first.

## 2026-05-13 scan

### Fixed in `cursor/python-style-violations-5dc7`

- [x] Google 2.4 "Exceptions": `/app/services/subscription_service.py`
  suppressed rollback failures with `except Exception: pass` while recording
  subscription usage errors. This was the worst open violation because it sits
  on the usage/accounting path: if the primary write failed and rollback also
  failed, the secondary database failure disappeared completely, blocking later
  billing investigation.

### Newly discovered open violations

- [ ] Google 2.4 "Exceptions": `/app/services/live_chat_service.py`
  catches broad `Exception` while waiting for prefill completion in
  `_flush_after_prefill`, then returns without logging. Log unexpected wait
  failures while still allowing cancellation to stop the background task.
- [ ] Google 2.4 "Exceptions": `/app/services/voice_cache_service.py`
  suppresses rollback failures with `except Exception: pass` in the save and
  access-stat update paths. Log rollback failure context so voice cache database
  errors remain diagnosable.
- [ ] Google 2.4 "Exceptions": `/app/services/push_notification_service.py`
  silently returns the original avatar URL when mobile image transformation
  fails. Log the transformation failure so push image delivery regressions are
  observable.
- [ ] Google 2.4 "Exceptions": `/app/services/memory_extraction_service.py`
  silently drops malformed metadata and messages with broad `Exception`
  fallbacks while reading chat history. Narrow expected JSON/data errors or log
  skipped rows so memory extraction loss is traceable.
- [ ] Google 2.4 "Exceptions": `/app/services/festival_memory_service.py`
  silently skips rows that fail chat-message JSON parsing. Log skipped rows or
  narrow the parser exceptions so festival memory inputs do not disappear
  without evidence.

## 2026-05-09 scan

### Fixed in `cursor/worst-python-style-violation-4605`

- [x] Google 2.12 "Default Argument Values": Pydantic schema fields used
  mutable list or dict defaults instead of `Field(default_factory=...)`.
  This was the worst current violation because these models sit on API
  boundaries and can leak hidden shared state or encode ambiguous request
  contracts.
  - `/app/schemas/notification.py`: `NotificationSendRequest.params = {}`
    also contradicted its `Optional` annotation.
  - `/app/schemas/response.py`: `PaginationData.list = []` and
    `PagedResponse.items = []`.
  - `/app/schemas/user.py`: `User.actions = []`.
  - `/backend/ops/schemas/evaluation.py`: `EvaluationSessionDetail.results`,
    `EvaluationSessionDetail.interactions`, and `QuestionFileUpload.warnings`
    used `[]`.

## 2026-05-11 scan

### Fixed in `cursor/worst-python-style-violation-cd9b`

- [x] Google 2.4 "Exceptions": `/tools/inty_v2_repl/backend_chat_ws.py`
  caught `BaseException` around the REPL WebSocket thread, reconnect,
  user-signed-on send, task shutdown, and socket close paths. This was the
  worst open violation because it formed the outer transport isolation layer
  for the companion REPL and could intercept process-level control exceptions
  such as `KeyboardInterrupt`, `SystemExit`, or coroutine cancellation instead
  of letting them propagate through the runtime.
- [x] Google 2.4 "Exceptions": `/tools/inty_v2_repl/backend_chat_ws.py`
  used `assert self._response_q is not None` as a runtime precondition in the
  reader loop. The bridge now raises an explicit `RuntimeError` because
  optimized Python can remove asserts.
- [x] Google 2.4 "Exceptions": `/tools/inty_v2_repl/backend_chat_ws.py`
  silently treated thread-safe queued pop failures as "no message" with a broad
  `except Exception`. The non-blocking REPL isolation point still suppresses
  the failure but now records it in logs.

### Newly discovered open violations

- [x] Google 2.4 "Exceptions":
  `/app/core/companion_harness/companion/significance_perception.py` catches broad
  `Exception` while parsing and extracting dual-LLM envelope candidates, then
  silently returns `None` or `[]`. Narrow to JSON/Pydantic/model-dump failures
  or log unexpected parser failures so malformed companion envelopes do not
  hide implementation bugs. Fixed in `cursor/agent-maintenance-task-e5ce`.
- [x] Google 2.4 "Exceptions":
  `/app/core/companion_harness/companion/llm_chat_runtime.py` catches broad
  `Exception` while reading LangSmith trace/run identifiers and silently
  returns empty strings. Log unexpected metadata extraction failures or narrow
  the expected attribute/key errors so trace-parent linkage is debuggable.
- [x] Google 2.4 "Exceptions": `/app/services/subscription_service.py`
  suppresses rollback failures with `except Exception: pass` while recording
  subscription usage errors. Log rollback failure context so billing/accounting
  failures do not lose secondary database error evidence. Fixed in
  `cursor/python-style-violations-5dc7`.

## 2026-05-10 scan

### Fixed in `cursor/worst-python-style-violation-b827`

- [x] Google 2.4 "Exceptions": `/app/core/companion_harness/companion/tool_background.py`
  caught `BaseException` at the background thread boundary and swallowed failures.
  This was the worst open violation because it could hide process-level control
  exceptions from the Companion Harness async tool path while still marking the
  background job idle.

### Newly discovered open violations

- [x] Google 2.4 "Exceptions": `/tools/inty_v2_repl/backend_chat_ws.py`
  catches `BaseException` in ten WebSocket bridge startup, reconnect, cleanup,
  and callback paths. Preserve thread/session isolation with narrower exception
  handling and re-raise process-level control exceptions. Fixed in
  `cursor/worst-python-style-violation-cd9b`.
- [ ] Google 2.4 "Exceptions": `/tools/llm.py` silently swallows multiple
  `Exception` blocks while loading LLM configuration and environment state.
  Log the suppressed failures or narrow the expected exception types.
- [ ] Google 2.4 "Exceptions": `/app/schemas/chat.py` has broad
  `except Exception` blocks that silently return original agent background
  values during URL transformation. Add structured logging and narrow expected
  exception types.
- [ ] Google 2.4 "Exceptions": `/app/services/user_analytics_service.py`
  suppresses analytics query failures with `except Exception: pass`; report
  skipped metric groups in logs so operational dashboards do not silently lose
  fields.
- [ ] Google 2.14 "True/False Evaluations":
  `/tools/scripts/create_email_password_user.py` uses SQLAlchemy
  `User.deleted_at == None`. Prefer `User.deleted_at.is_(None)` for explicit
  SQL `IS NULL` semantics.

### Open violations

- [ ] Google 2.4 "Exceptions": `/app/core/companion_harness/llm/langsmith_completion_enrich.py`
  uses multiple `except Exception: pass` blocks around LangSmith enrichment
  monkey-patch code. Log suppressed failures and move import-time patching to
  an explicit initialization path if possible.
- [ ] Google 2.4 "Exceptions": `/app/schemas/agent.py` has several broad
  `except Exception` blocks that silently return `None` or the original value
  while transforming URLs and metadata. Add structured logging and narrow the
  expected exception types.
- [ ] Google 2.4 "Exceptions": `/app/core/companion_harness/companion/turn.py`
  catches `BaseException`, mutates the exception object, then suppresses
  metadata tagging errors. Avoid dynamic mutation of arbitrary exceptions and
  log secondary failures.
- [x] Google 2.4 "Exceptions": `/tools/inty_v2_repl/backend_chat_ws.py` uses
  `assert self._response_q is not None` as a runtime precondition. Replace it
  with an explicit `RuntimeError` because optimized Python removes asserts.
  Fixed in `cursor/worst-python-style-violation-cd9b`.
- [ ] Google 2.5 "Mutable Global State": `/tools/scripts/migrate_generated_images.py`
  keeps `_session_id_to_chat_cache` as mutable module-level state without an
  explicit invalidation path. Prefer caller-owned cache state or a force-reload
  option.
- [ ] Google 2.14 "True/False Evaluations": `/app/api/v1/endpoints/auth.py`
  uses SQLAlchemy `User.deleted_at == None`. Prefer `User.deleted_at.is_(None)`
  for explicit SQL `IS NULL` semantics.
