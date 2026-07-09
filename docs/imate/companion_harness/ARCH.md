# Companion Harness: code architecture

> Describes the logical structure of the Python implementation under [app/core/companion_harness/](/app/core/companion_harness/) as aligned with [DESIGN.md](/docs/imate/companion_harness/DESIGN.md).
> This is primarily a user-view target structure (with gaps and legacy vestiges).
> Before assuming a behavior is implemented, read the code; do not treat this doc as an implementation checklist.

## Purpose

Lock down the framework layout so new code follows the established structure.
Package, module, and file positioning lives in each `__init__.py`, module docstring, and file-level docstring — list the tree and read those for detail.

## How to read

- [DESIGN.md](/docs/imate/companion_harness/DESIGN.md) — what the harness should do (user view, domain concepts, turn tracks, memory model).
- This doc — how the code is layered and wired (concept → package, dependency direction, load-bearing seams).
- [app/core/companion_harness/](/app/core/companion_harness/) — source of truth for what exists today.

## Concept-to-code mapping

Maps DESIGN.md concepts to the packages that realize them. Not a package catalog.

Each line is tagged **`[importance · DESIGN conformity]`**:

- **Importance** — `core` (kernel / relationship loop), `supporting` (infrastructure or session overlay the kernel needs), `peripheral` (gateway or campaign-facing; omit without breaking the bond model).
- **DESIGN conformity** — `good` (matches DESIGN.md target in active code paths), `partial` (right direction, named gaps vs target), `legacy` (still on a path being replaced), `unclear` (open design or working hypothesis not validated in code).

- **`[peripheral · good]` Channel** — manifestation surface for one relationship; channel adapters live outside this tree (Ops services, WebSocket glue). Harness-side channel types and runtime context: [companion/runtime_channel.py](/app/core/companion_harness/companion/runtime_channel.py). Multi-medium scope keys: [agent_channel/](/app/core/companion_harness/agent_channel/).
- **`[supporting · good]` InputQueue & OutputQueue** — durable per-scope message buffering between gateway and harness: [agentic_companion/](/app/core/agentic_companion/).
- **`[core · good]` Companion session & scope** — one MemoryStore per paired user scope, lifecycle and turn_lock: [companion/manager.py](/app/core/companion_harness/companion/manager.py).
- **`[core · good]` Turn tracks** — `CompanionTurnTrack` routing to the turn executor: [companion/turn_track.py](/app/core/companion_harness/companion/turn_track.py), [companion/models.py](/app/core/companion_harness/companion/models.py). Track list and semantics: DESIGN.md § Turn tracks.
- **`[core · good]` Turn execution (AwakeTurn)** — single-turn LLM loop, transcript append, tool rounds: [companion/turn.py](/app/core/companion_harness/companion/turn.py), [companion/turn_pipeline.py](/app/core/companion_harness/companion/turn_pipeline.py).
- **`[core · good]` Agentic loop (queue-served user chat)** — drain InputQueue, run one user-facing turn, stream to OutputQueue: [loop/agentic_loop.py](/app/core/companion_harness/loop/agentic_loop.py) via [agentic_companion/companion.py](/app/core/agentic_companion/companion.py).
- **`[core · partial]` Prompt assembly** — system-prefix slices and track-composed bundles; target projection pipeline in [prompting/projection/](/app/core/companion_harness/prompting/projection/) + [memory/retrieval.py](/app/core/companion_harness/memory/retrieval.py): DESIGN.md § Prompt content categories. Code: [prompting/](/app/core/companion_harness/prompting/) (including [system_messages.py](/app/core/companion_harness/prompting/system_messages.py)), [prompt_builder.py](/app/core/companion_harness/prompt_builder.py), [companion/prompt_stack.py](/app/core/companion_harness/companion/prompt_stack.py), [companion/prompts/](/app/core/companion_harness/companion/prompts/) (MD seeds). Bootstrap/settled user chat on `PromptBuilder`; greeting, proactive, scheduled, monolog still on `prompt_stack` / `build_system_messages` (#3463 migration).
- **`[core · partial]` MemoryStore & MemDocs** — versioned workspace documents, transcript JSONL, consolidation: [memory/](/app/core/companion_harness/memory/). Detail: [MEMORY_STORE.md](/docs/imate/companion_harness/MEMORY_STORE.md). Relationship state is implicit in MemDocs today; explicit CRS model and memory hierarchy are open (DESIGN.md § CRS, § 记忆模型).
- **`[core · good]` Tools** — schema, in-turn sync execution, async background tool threads: [tools/](/app/core/companion_harness/tools/).
- **`[supporting · good]` LLM transport** — provider calls, LangSmith enrichment: [llm/](/app/core/companion_harness/llm/), [providers/](/app/core/companion_harness/providers/).
- **`[core · good]` Inner-tick** — idle poll fires monolog, autonomy, proactive, scheduled, dreaming due checks: [runtime/inner_tick_fire.py](/app/core/companion_harness/runtime/inner_tick_fire.py). Schedule and kind mapping: [companion/inner_tick_schedule.py](/app/core/companion_harness/companion/inner_tick_schedule.py).
- **`[core · partial]` Dreaming (batch memory curation)** — end-of-day MemDoc consolidation, not a user-visible turn: [runtime/dreaming_batch.py](/app/core/companion_harness/runtime/dreaming_batch.py), [memory/dreaming_consolidation.py](/app/core/companion_harness/memory/dreaming_consolidation.py). Memory-phase invariant is enforced; CRS axis → consolidation mapping remains a working hypothesis (DESIGN.md § 记忆模型).
- **`[supporting · good]` Experience profile** — session switches and turn overlays from context.json: [experience_profile/](/app/core/companion_harness/experience_profile/).
- **`[supporting · unclear]` Living Sphere / Techno Core** — seeded into MemoryStore from sibling packages [app/living_sphere/](/app/living_sphere/), [app/techno_core/](/app/techno_core/); harness reads/writes via memory and tools. Prototype MemDoc injection, not the target world engine (DESIGN.md § 记忆模型, [FR_WORLD_ENGINE.md](/docs/imate/companion_harness/FR_WORLD_ENGINE.md)).

## Package layering

Dependency direction: outer layers call inward; leaf packages do not import the kernel.

```package-layering
┌─────────────────────────────────────────────────────────────┐
│  Channel adapters (outside harness: app/services, Ops)    │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  Serving (app/core/agentic_companion)                       │
│  queues · AgenticCompanion · turn seam                      │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  Companion harness serving (loop · runtime)                 │
│  AgenticLoop · inner_tick_fire · dreaming_batch             │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  Kernel                                                     │
│  companion                                                  │
│  (session, turn executor, tracks, bootstrap, dreaming rules)│
└────────────────────────────┬────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐  ┌─────────────────┐  ┌───────────────┐
│ prompting     │  │ memory          │  │ tools         │
│ prompt_builder│  │ (MemoryStore)   │  │ (registry,    │
│               │  │                 │  │  dispatchers) │
└───────────────┘  └─────────────────┘  └───────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             ▼
              ┌──────────────────────────┐
              │ llm · providers          │
              │ experience_profile       │
              └──────────────────────────┘
```

Import rule (prototype): sibling orchestration packages import leaf layers; leaves import each other only where needed and never import companion turn orchestration.

## Turn runtime flow

Load-bearing seams for one inbound user message. Track-specific branches (greeting, proactive, inner-tick) share the same kernel entry; see DESIGN.md § Harness Pipelines and § Turn tracks.

```turn-runtime-flow
 inbound event (WS / IM adapter)
        │
        ▼
 enqueue ──► InputQueue (agentic_companion)
        │
        ▼
 AgenticCompanion.drain ──► AgenticLoop (loop)
        │
        ▼
 track pick ──► run_turn (companion)
        │
        ├──► prompt assembly (prompting / prompt_stack / prompt_builder)
        │
        ├──► LLM call (llm / providers)
        │
        ├──► tool round (tools) ──► optional tool_background thread
        │
        └──► append transcript + side effects (memory / MemoryStore)
        │
        ▼
 OutputQueue ──► channel delivery

 parallel (scope inner-tick poll, under turn_lock):
        scheduled (no presence) · monolog · autonomy · dreaming due
                                              │
                                              └──► run_turn (same kernel)

 end-of-day (DreamingBatch, under turn_lock):
        dreaming_batch (runtime) ──► dreaming_consolidation (memory) ──► MemDoc curation
```

AwakeTurn vs DreamingBatch memory-phase split is enforced in code; see Invariants below.

## Invariants and conventions

- **Memory phase invariants** — AwakeTurn only appends transcript and tool side effects; MemDoc batch curation runs in DreamingBatch only. Canonical definitions: [companion/turn_invariants.py](/app/core/companion_harness/companion/turn_invariants.py), [companion/lifecycle_invariants.py](/app/core/companion_harness/companion/lifecycle_invariants.py), [companion/AGENTS.md](/app/core/companion_harness/companion/AGENTS.md).
- **Turn-lock contract** — scope serialization via CompanionSession.turn_lock; runtime batch orchestrators assume the lock is already held. See [runtime/__init__.py](/app/core/companion_harness/runtime/__init__.py).
- **Where detail lives** — package intent in `__init__.py`; module and file behavior in module/file docstrings. Do not duplicate that catalog here.
- **Refactor residue (do not build into)** — empty or placeholder dirs: contracts/, official_helper/, loop/one_llm/, loop/two_llm/, loop/parity/, companion/autonomy/ (AGENTS.md only). Prefer the flat modules in companion/ and loop/ until reorg lands (#3409).

## See also

- [DESIGN.md](/docs/imate/companion_harness/DESIGN.md) — user-view architecture, domain concepts, turn tracks, prompt axes.
- [GLOSSARY.md](/docs/imate/companion_harness/GLOSSARY.md) — terminology and direction (upstream/downstream, foreground/background).
- [MEMORY_STORE.md](/docs/imate/companion_harness/MEMORY_STORE.md) — MemDoc model and persistence.
- [MEMORY_STORE.md](/docs/imate/companion_harness/MEMORY_STORE.md) — MemDoc model, persistence, and [Memory projection](/docs/imate/companion_harness/MEMORY_STORE.md#memory-projection) read-side summary.
- [companion_harness/AGENTS.md](/app/core/companion_harness/AGENTS.md) — prototype scope, non-goals, tech stack.
- [companion/AGENTS.md](/app/core/companion_harness/companion/AGENTS.md) — turn tracks, memory-phase invariants, lifecycle rules.
