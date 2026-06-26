"""Memory projection stage: order, budget, and render selected slices into PromptPlan.

Target pipeline (not fully wired today):

    MemoryStore → [RETRIEVAL / SELECTION] → [PROJECTION] → PromptPlan

**Three materialization regions** (maps to DESIGN.md content category × runtime organization):

- Static backbone — Doctrine, Capability, Output (+ peripheral channel format); code-owned,
  position-stable; no MemDoc metadata.
- Dynamic MemDoc region — Persona (+ Living Sphere / Techno Core when injected); ordered
  by score within slot.
- Conversation region — projected transcript (not literal replay); see ``TranscriptProjection``.

**Today**: ``PromptBuilder`` and ``prompt_stack`` assemble prompts imperatively, skipping
an explicit selection stage. Eager reads via ``load_prompt_bundle`` (#3521).

**AwakeTurn invariant**: projection only reads MemoryStore; MemDoc curation stays in
dreaming batch (``consolidate_memory_during_dreaming``).

TODO(memory-projection-pipeline): Wire ``project_slices_to_prompt_plan`` after
``select_slices_for_turn`` lands (#3523).
"""
