"""Companion memory-phase invariants (AwakeTurn / DreamingBatch).

AwakeTurn — all ``CompanionTurnTrack`` entries via ``run_turn`` plus spawned
``tool_background`` — may only append transcript JSONL and run ``tool_background``
side effects (incremental tool writes such as ``update_user_md``).

DreamingBatch — ``run_dreaming_batch_if_due`` — MemoryDoc **batch curation**
must go only through ``consolidate_memory_during_dreaming`` (checkpoint and
observability are orchestration, not curation).

Architecture enforcement: ``.cursor/skills/scripts/check_companion_turn_invariants.py``.

TODO(crs-write-lattice): When ``TrackWritePolicy`` (#3367) lands, extend CI checker to enforce
short-frame awake tracks cannot batch-curate long-frame MemoryDocs (canon #3365, epic #3341).
"""

from __future__ import annotations

from .models import CompanionTurnTrack

DREAMING_BATCH_ORCHESTRATOR = "run_dreaming_batch_if_due"
DREAMING_BATCH_CURATION_ENTRY = "consolidate_memory_during_dreaming"

AWAKE_TURN_TRACKS: frozenset[CompanionTurnTrack] = frozenset(CompanionTurnTrack)

# Dot-module paths under repo root (``app/...`` → ``app....``).
CONSOLIDATE_MEMORY_DURING_DREAMING_IMPORT_ALLOWLIST: frozenset[str] = frozenset(
    {
        "app.core.companion_harness.memory.dreaming_consolidation",
        "app.core.companion_harness.runtime.dreaming_batch",
    }
)

AWAKE_TURN_ORCHESTRATOR_RELATIVE_PATHS: frozenset[str] = frozenset(
    {
        "app/core/companion_harness/companion/turn.py",
        "app/core/companion_harness/companion/turn_pipeline.py",
        "app/core/companion_harness/tools/tool_background.py",
    }
)

DREAMING_CURATOR_CALLABLES: frozenset[str] = frozenset(
    {
        "_rewrite_dreaming_daily_gist_md",
        "_rewrite_memory_md",
        "_rewrite_user_md",
        "_rewrite_style_md",
        "_rewrite_soul_md",
        "_rewrite_companionship_md",
        "compact_living_sphere_if_pending",
        "compact_living_sphere_batch",
    }
)

DREAMING_CURATOR_CALLER_RELATIVE_PATHS: frozenset[str] = frozenset(
    {
        "app/core/companion_harness/memory/dreaming_consolidation.py",
        "app/core/companion_harness/memory/living_sphere_curator.py",
    }
)

FORBIDDEN_LEGACY_MEMORY_SYMBOLS: frozenset[str] = frozenset(
    {
        "memory_pipeline",
        "defer_memory_update",
        "MemoryPipelineConfig",
    }
)

AWAKE_TURN_TRANSCRIPT_ONLY_RELATIVE_PATH: str = (
    "app/core/companion_harness/companion/turn.py"
)

AWAKE_TURN_ALLOWED_STORE_MUTATIONS: frozenset[str] = frozenset(
    {
        "append_jsonl_record",
    }
)

AWAKE_TURN_FORBIDDEN_STORE_MUTATIONS: frozenset[str] = frozenset(
    {
        "write_document",
        "append_line",
    }
)
