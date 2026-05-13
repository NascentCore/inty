Summary: Logged LangSmith companion parent trace/run id extraction failures so trace linkage issues remain debuggable.

- Picked the open Google 2.4 exception-handling maintenance TODO in `P2_FIX_PYTHON_STYLE_VIOLATIONS.md`.
- Replaced duplicated silent best-effort id extraction with a shared helper that logs unexpected extraction errors before returning the existing empty-string fallback.
- Marked the maintenance TODO as fixed on `cursor/agent-maintenance-task-23ab`.

Follow-ups: None.
