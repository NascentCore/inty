# Memory Projection

> Generated entirely by the Cursor agent as a design capture (2026-06). Gist, not transcript.

## Core idea

The prompt is a deterministic, budget-bounded projection of a versioned slice space (MemDocs + conversation turns, differing only by TTL), shaped by the agent only through slice content/metadata edits and offline slot-algebra morphs.

## Concrete designs (decided)

- Pipeline has a selection stage between storage and prompt:

```
MemoryStore (all slices)
      |
      v
[ RETRIEVAL / SELECTION ]   which slices are candidates THIS turn
      |
      v
[ PROJECTION ]   order (stability-first) + budget + render
      |
      v
   PromptPlan
```

- Three materialization regions:
  - Static backbone: code-owned, position-stable (doctrine, capability, output contract). Carries no metadata; guarantees format/safety invariants regardless of memory state.
  - Dynamic MemDoc region: projected and ordered by score (persona, relationship, world, memory).
  - Conversation region: a projected transcript, not literal replay. Old turns migrate into memory slices; ephemeral/synthetic turns (e.g. the proactive-chat eliciting message) are dropped after use. A turn is just a short-TTL slice.
- Authority split (the safety/determinism boundary): global slot order is code-owned; intra-slot inclusion and order are metadata-driven; the agent never reorders structural slots. The per-turn prompt is reconstructable from a slice snapshot + context + clock.
- Ordering invariant is stability-first for KV-cache prefix reuse: most durable slices at the head, most volatile at the tail. Importance sorts only within a stability band.
  - effective_order = (slot_rank, stability_band, relevance x priority x decay)
  - relevance is just the retrieval term; resident slices pin relevance to 1.
- Frontmatter metadata on projected MemDocs (YAML block at top of the markdown):
  - Core: slot, priority (within-slot 0-100), pinned (always included, exempt from budget), expires_at (omit after expiry).
  - Extensions: active, heading, source, updated_at.
  - Edited via a dedicated set_doc_metadata op (atomic, auditable), not whole-doc rewrite.
- slot vs the current hardcoded taxonomy: slot moves membership + heading from code into data; the harness keeps only a small slot -> rank table; adding a new doc needs no code change; a new slot category is a one-line rank entry.
- Retrieval tiers mirror human memory:
  - Resident (always candidate): doctrine, identity/persona core, control state.
  - Verbatim window: recent turns kept as exact messages.
  - Associative: older/larger material fetched on demand by relevance.
- Verbatim vs gist horizon (human-faithful):
  - Verbatim window is anchored to the dreaming consolidation cycle (about one day), with a token budget as the hard cap. Sleep/dreaming consolidates episodic -> semantic, then resets the window.
  - Salience pins keep select emotionally important exact lines beyond the window.
  - Gist (compacted MemDocs) covers weeks-to-months.
- Retrieval stance: MemoryStore stays the single source of truth.
  - Start with structured navigation over the slot tree + lexical search over markdown (zero infra, deterministic, explainable).
  - Add a local semantic index as a derived candidate generator; final selection re-reads the canonical MemDoc.
  - External memory services are optional, behind a return-slice-refs interface, off by default given single-human intimacy/privacy.
- Slot algebra (offline compaction ops run by DREAMING), each an auditable transform recording derived_from provenance:

```
GENERATE                 AGGREGATE (compact up)         SPLIT (refine down)
spawn a slot             day -> week -> month           companionship (summary)
"college student"        children retire via                     |
   -> slot: college_life expires_at                     casual        intimacy

COMPACTION LADDER (same data, increasing abstraction)
  high abstraction / durable / cache-stable / prompt HEAD
    month
      week
        day  day  day
          live conversation turns (verbatim, short TTL, prompt TAIL)
  low abstraction / volatile / cache-busting
```

## Speculative / less settled

- Typed message ADTs (system/user/assistant/tool) whose real value is stable identity + provenance, enabling doc-keyed targeted refresh instead of rebuild-all.
- LLM-proposed new slots and morphs; harness validates and assigns rank + budget.
- Cross-slot token-budget allocation policy, layered on top of within-slot priority.
- Exposing a PromptPlan meta-description to the model, constrained to metadata edits rather than free message reordering.
- Per-turn slice snapshot for eval reproducibility and rehydration of compacted branches.

## References

- Docs: MEMORY_STORE.md, AUTONOMY.md, DESIGN.md, BRAINSTORM.md, GLOSSARY.md
- Issues: #3453 (PromptTemplate named-slot), #3398 (dual vs single-LLM epic), #3460 (AgenticLoop consolidation), #3376 (dreaming day rollup)
- Code: app/core/companion_harness/prompt_builder.py, app/core/companion_harness/prompting/tracks.py, app/core/companion_harness/memory/dreaming_consolidation.py
- External inspiration: fuzzy-trace theory (verbatim vs gist), Ebbinghaus forgetting curve, Pie programmable serving, claude-mem, Human-like Memory
