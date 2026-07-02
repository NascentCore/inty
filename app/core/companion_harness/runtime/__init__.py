"""Companion Harness runtime layer: turn orchestration and batch memory phases.

This package holds scope-level execution seams (``run_turn`` tracks, DreamingBatch,
WebSocket coordination) that wire memory, LLM, tools, and observability. Domain rules
for sleeping-state dreaming live in ``companion.dreaming``; callers invoke runtime
entry points after resolving a ``CompanionSession``.

**Lock contract (prototype):**

- Callers must already hold scope ``CompanionSession.turn_lock`` (#3272) before invoking
  runtime batch orchestrators.
- Runtime modules do **not** acquire ``turn_lock``.
- Authoritative ``dreaming_due`` checks run inside the lock within
  ``dreaming_batch.run_dreaming_batch_if_due``; callers must not decide due/skip
  outside the lock.
- Inner-tick AwakeTurn due checks and kernel fires live in
  ``companion_harness.runtime.inner_tick_fire``; channel glue in
  ``app.services.agentic_companion.inner_tick_fire`` holds ``turn_lock`` before calling.
- One signed-on presence per paired user (#3272); user chat and inner-tick
  (including dreaming) serialize on scope ``turn_lock``.
- Scope inner-tick worker (#3255) runs monolog, autonomy, dreaming without presence
  via ``scope_inner_tick_poll`` / ``scope_inner_tick_fire``.
- Postgres advisory lock for multi-process (#3271) remains future work.

TODO(world-engine-agent-harness): Extract shared AgentHarness turn spine — #3702
(perceive → load hidden state → BehaviorPolicy → mailbox emit → evolve state).
CompanionHarness delegates transparently (epic #3700).

TODO(world-engine-mailbox-spawn): Add Mailbox send/receive and SpawnRegistry — #3703
(spawn/dismiss/hibernate) APIs; Phase 1 API-only, no prompt injection (epic #3700).

TODO(world-engine-firefly-test): Firefly runner + SubAgentSupervisor — #3705
(pytest harness only; no production LLM) (epic #3700).
"""
