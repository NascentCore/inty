# Fix Violations of Python Style Guides

This file records the latest discovered Google Python Style Guide violations
for automations that reference the non-prioritized maintenance path. Historical
scan history remains in `P2_FIX_PYTHON_STYLE_VIOLATIONS.md`.

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

