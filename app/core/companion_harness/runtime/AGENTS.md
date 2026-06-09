# Runtime

Turn orchestration and batch memory phases for one paired companion scope.

## AwakeTurn vs DreamingBatch

- **AwakeTurn** — all ``CompanionTurnTrack`` entries via ``run_turn`` plus spawned
  ``tool_background``: only append transcript JSONL and incremental tool writes.
  Canonical paths: ``turn.py``, ``turn_pipeline.py``; invariants in ``turn_invariants.py``.
- **DreamingBatch** — ``run_dreaming_batch_if_due`` (``dreaming_batch.py``): sleeping-state
  MemoryDoc batch curation only via ``consolidate_memory_during_dreaming`` in ``memory/``.
  Due checks and checkpoint state live in ``dreaming.py``; observability in
  ``dreaming_observability.py``.

Call chain: inner-tick / ``companion_chat_service`` → ``run_dreaming_batch_if_due`` →
``consolidate_memory_during_dreaming``.

## Lock contract (prototype)

Callers must hold presence ``Coordinator.turn_lock`` before batch orchestrators.
Runtime modules do **not** acquire ``turn_lock``.

## LLM invocation tracks

- User chat: respond to user message
- Greeting: proactive greeting when user signed on
- Proactive chat: proactive messages while user is idle
- Scheduled activity: future-scheduled inner-tick fires
- Maintenance: background inner-tick transcript compaction (hidden from users)

## Prototype notes

One presence (single tab / wire) per paired user; no multi-presence.
Production user entry: WebSocket + Weixin only.
