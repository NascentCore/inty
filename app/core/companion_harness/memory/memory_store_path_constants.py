"""Canonical scope-relative MemoryStore document path strings (canonical path constants).

Generated entirely by Cursor agent.

Single source for MemDoc keys shared by ``MemoryStoreScopePaths``, ORM
``document_kind`` mapping, and tool modules that read/write one path.
"""

from __future__ import annotations

from typing import Final

IDENTITY_MD_REL: Final[str] = "IDENTITY.md"
ABOUT_MD_REL: Final[str] = "ABOUT.md"
SOUL_MD_REL: Final[str] = "SOUL.md"
STYLE_MD_REL: Final[str] = "STYLE.md"
USER_MD_REL: Final[str] = "USER.md"
MEMORY_MD_REL: Final[str] = "MEMORY.md"
CHANNELS_MD_REL: Final[str] = "CHANNELS.md"
COMPANIONSHIP_MD_REL: Final[str] = "COMPANIONSHIP.md"
TECHNO_CORE_MD_REL: Final[str] = "TECHNO_CORE.md"
LIVING_SPHERE_MD_REL: Final[str] = "LIVING_SPHERE.md"
TOOLS_MD_REL: Final[str] = "TOOLS.md"
SIGNIFICANCE_PERCEPTION_MD_REL: Final[str] = "SIGNIFICANCE_PERCEPTION.md"
AXIOM_MD_REL: Final[str] = "AXIOM.md"
BOOTSTRAP_MD_REL: Final[str] = "BOOTSTRAP.md"
BOOTSTRAP_TELEGRAM_PROFILE_MD_REL: Final[str] = "BOOTSTRAP_TELEGRAM_PROFILE.md"
HARNESS_MD_REL: Final[str] = "HARNESS.md"
INTY_MD_REL: Final[str] = "INTY.md"
OUTPUT_FORMAT_IM_DM_MD_REL: Final[str] = "OUTPUT_FORMAT_IM_DM.md"
SAFETY_MD_REL: Final[str] = "SAFETY.md"
TRANSCRIPT_JSONL_REL: Final[str] = "transcript.jsonl"
TRANSCRIPT_INNER_TICK_JSONL_REL: Final[str] = "transcript_inner_tick.jsonl"
CONTEXT_JSON_REL: Final[str] = "context.json"
AI_PRIVATE_MD_REL: Final[str] = "ai_private.md"
AI_PRIVATE_JSONL_REL: Final[str] = "ai_private.jsonl"
LIFE_CURRENTS_MD_REL: Final[str] = "LIFE_CURRENTS.md"
CHAT_HISTORY_MD_REL: Final[str] = "CHAT_HISTORY.md"
TECHNO_CORE_EVENTS_JSONL_REL: Final[str] = "techno_core_events.jsonl"
LIVING_SPHERE_UPDATES_JSONL_REL: Final[str] = "living_sphere_updates.jsonl"
TOOL_BACKGROUND_JSONL_REL: Final[str] = "tool_background.jsonl"
GENERATED_IMAGES_INDEX_JSONL_REL: Final[str] = "generated_images/index.jsonl"
COMPANION_RUNTIME_EVENTS_JSONL_REL: Final[str] = ".companion_runtime_events.jsonl"
COMPANION_USER_FEEDBACK_JSONL_REL: Final[str] = ".companion_user_feedback.jsonl"
COMPANION_DREAMING_STATE_JSON_REL: Final[str] = ".companion_dreaming_state.json"
COMPANION_LIVING_SPHERE_CURATOR_JSON_REL: Final[str] = (
    ".companion_living_sphere_curator.json"
)
COMPANION_CONTEXT_COMPACTION_STATE_JSON_REL: Final[str] = (
    ".companion_context_compaction_state.json"
)
COMPANION_SCHEDULE_TASKS_JSON_REL: Final[str] = ".companion_schedule_tasks.json"
INTY_V2_LIVING_SPHERE_CURATOR_JSON_REL: Final[str] = (
    ".inty_v2_living_sphere_curator.json"
)
INTY_V2_CONTEXT_COMPACTION_STATE_JSON_REL: Final[str] = (
    ".inty_v2_context_compaction_state.json"
)
INTY_V2_SCHEDULE_TASKS_JSON_REL: Final[str] = ".inty_v2_schedule_tasks.json"
INTY_V2_DREAMING_STATE_JSON_REL: Final[str] = ".inty_v2_dreaming_state.json"
MEMORY_DAILY_GIST_DIR_REL: Final[str] = "memory/daily"


def memory_daily_gist_rel(day: str) -> str:
    """Scope-relative daily gist path (``memory/daily/<date>.md``)."""
    assert day
    return f"{MEMORY_DAILY_GIST_DIR_REL}/{day}.md"
