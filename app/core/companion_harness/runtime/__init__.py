"""Companion Harness runtime layer: turn orchestration and batch memory phases.

This package holds scope-level execution seams (``run_turn`` tracks, DreamingBatch,
WebSocket coordination) that wire memory, LLM, tools, and observability. Domain rules
for sleeping-state dreaming live in ``companion.dreaming``; callers invoke runtime
entry points after resolving a ``CompanionSession``.

**Lock contract (prototype):**

- Callers must already hold presence ``Coordinator.turn_lock`` (or equivalent
  single-writer exclusion) before invoking runtime batch orchestrators.
- Runtime modules do **not** acquire ``turn_lock``.
- Authoritative ``dreaming_due`` checks run inside the lock within
  ``dreaming_batch.run_dreaming_batch_if_due``; callers must not decide due/skip
  outside the lock.
- One signed-on presence per paired user (#3272); user chat and inner-tick
  (including dreaming) serialize on the same lock.
- Future: scope-level worker (#3255, Epic #3373) and Postgres advisory lock (#3271).

"""
