"""Default values for agent.companion_harness companion-related fields (utils-only; no app.core imports)."""

from __future__ import annotations

from typing import Any

# Default companion transcript compaction when config.yaml omits the key.
# Set agent.companion_harness.transcript.compaction to null in YAML to disable.
DEFAULT_COMPANION_FEATURE_COMPACTION: dict[str, Any] = {
    "max_context_chars": 12000,
    "keep_recent_messages": 24,
    "max_messages_per_episode": 6,
    "max_episodic_entries": 8,
    "max_semantic_entries": 8,
    "summary_max_chars": 800,
    "retrieval_episode_count": 3,
    "retrieval_semantic_count": 4,
    "retrieval_open_loop_count": 3,
}
