# Companion

Memory processing pipeline. Abstract **coherent scope state** and **behavior display**
(text / image / voice-audio). Production user entry: **WebSocket + Weixin only**; HTTP
chat not planned unless explicitly requested.

## LLM invocation tracks

- User chat: respond to user message
- Greeting: proactive greeting message when detected user signed on
- Proactive chat: proactive messages sent to user when user is not sending any message
- Scheduled activity: activities that are scheduled to be fired in the future
- Maintenance: regular maintenance, background & hidden from users, to process & reorganize chat messages (restricted inner-tick tool set).
- Autonomy: silent self-directed work during user idle — reads/writes ``LIFE_CURRENTS.md`` with an open tool set; never delivers to the user (see ``docs/companion_harness/AUTONOMY.md``).
  - TODO(narrow-maintenance): Shrink maintenance to memory-reorg only; profile/MemoryDoc sync belongs in **dreaming**.

## Memory phase invariants

- **AwakeTurn** (all ``CompanionTurnTrack`` → ``run_turn`` + spawned ``tool_background``): only
  append transcript JSONL and ``tool_background`` side effects — no MemoryDoc batch curation.
- **DreamingBatch** (``run_dreaming_batch_for_session``): MemoryDoc batch curation only via
  ``consolidate_memory_during_dreaming`` (checkpoint / observability are orchestration).

Canonical constants and CI enforcement: ``turn_invariants.py``;
``.cursor/skills/scripts/check_companion_turn_invariants.py``.

## Memory lifecycle invariants

Codified in ``lifecycle_invariants.py``; enforced by
``tests/app/core/companion_harness/companion/test_lifecycle_invariants.py``.

- **AwakeTurn** (``run_companion_*_turn`` → ``_run_companion_turn_core``): kernel
  (``turn.py``, ``turn_engine.py``) **only** ``append_jsonl_record`` on
  ``transcript.jsonl`` / ``transcript_inner_tick.jsonl``. Async ``tool_background``
  may append ``tool_background.jsonl`` (and transcript rows for tool-bg assistant
  lines). **No** ``consolidate_memory_during_dreaming``, **no** automatic curator
  writes to ``MEMORY.md`` / ``USER.md`` / ``STYLE.md`` / ``SOUL.md`` /
  ``memory/daily/`` / ``LIVING_SPHERE.md``.
- **DreamingBatch** (``run_dreaming_batch_for_session``): memory curation **only**
  via ``consolidate_memory_during_dreaming`` (plus ``.companion_dreaming_state.json``
  checkpoint — not MemoryDoc curation).

Carve-outs (documented, not kernel): bootstrap ``companion_update_prompt_slice``,
``transcript_compaction`` state JSON, ``companion_runtime_events.jsonl``, session-init
``context.json``, tool-driven workspace writes during a turn.

## Prototype notes

For this prototype, **one presence** (single tab / wire) per paired user, no multi-presence.
