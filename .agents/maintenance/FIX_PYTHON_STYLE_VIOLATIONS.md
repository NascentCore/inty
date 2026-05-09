# Fix Violations of Python Style Guides

This file tracks discovered violations of Google's Python Style Guide so
maintenance agents can fix the highest-impact item first.

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

### Open violations

- [ ] Google 2.4 "Exceptions": `/app/core/agentic_kernel/companion/tool_background.py`
  catches `BaseException` in the background tool runner and does not propagate
  failures to the foreground control path. Replace with a narrower exception
  boundary and an explicit failure event or future.
- [ ] Google 2.4 "Exceptions": `/app/core/agentic_kernel/llm/langsmith_completion_enrich.py`
  uses multiple `except Exception: pass` blocks around LangSmith enrichment
  monkey-patch code. Log suppressed failures and move import-time patching to
  an explicit initialization path if possible.
- [ ] Google 2.4 "Exceptions": `/app/schemas/agent.py` has several broad
  `except Exception` blocks that silently return `None` or the original value
  while transforming URLs and metadata. Add structured logging and narrow the
  expected exception types.
- [ ] Google 2.4 "Exceptions": `/app/core/agentic_kernel/companion/turn.py`
  catches `BaseException`, mutates the exception object, then suppresses
  metadata tagging errors. Avoid dynamic mutation of arbitrary exceptions and
  log secondary failures.
- [ ] Google 2.4 "Exceptions": `/tools/inty_v2_repl/backend_chat_ws.py` uses
  `assert self._response_q is not None` as a runtime precondition. Replace it
  with an explicit `RuntimeError` because optimized Python removes asserts.
- [ ] Google 2.5 "Mutable Global State": `/scripts/migrate_generated_images.py`
  keeps `_session_id_to_chat_cache` as mutable module-level state without an
  explicit invalidation path. Prefer caller-owned cache state or a force-reload
  option.
- [ ] Google 2.14 "True/False Evaluations": `/app/api/v1/endpoints/auth.py`
  uses SQLAlchemy `User.deleted_at == None`. Prefer `User.deleted_at.is_(None)`
  for explicit SQL `IS NULL` semantics.
