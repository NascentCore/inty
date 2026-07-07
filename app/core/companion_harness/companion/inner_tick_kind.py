"""Inner-tick kind registry: one binding row per awake idle-poll turn type.

``InnerTickKind`` is the canonical identity; ``INNER_TICK_KINDS`` holds the
cross-layer attributes that otherwise fan out across track, activity, throttle,
prompt builders, and wire metadata. ``DREAMING`` is intentionally excluded (memory
batch, not a turn).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.prompting.bundle import PromptBundle

from .models import (
    CompanionTurnTrack,
    ContextMeta,
    InnerTickActivity,
    InnerTickKind,
    InnerTickThrottleKind,
    MONOLOG_INNER_TICK_CHAT_HISTORY_USER_MARKER,
)

from .proactive_chat import PROACTIVE_CHAT_TRANSCRIPT_USER_MARKER
from .prompts.system_messages import (
    build_system_messages_for_inner_tick_autonomy,
    build_system_messages_for_inner_tick_monolog,
)

PromptBuilder = Callable[
    [PromptBundle, ContextMeta, MemoryStore], list[dict[str, Any]]
]


@dataclass(frozen=True)
class InnerTickKindSpec:
    """Single source of truth for one inner-tick kind's cross-layer attributes.

    The only edit site when renaming a kind or adding one. Holds data plus a
    single typed prompt callable; no method-name or schema-field strings.
    """

    activity: InnerTickActivity
    turn_track: CompanionTurnTrack
    throttle_kind: InnerTickThrottleKind | None
    chat_history_marker: str
    suppresses_user_delivery: bool
    async_tool_prompt_builder: PromptBuilder | None


INNER_TICK_KINDS: dict[InnerTickKind, InnerTickKindSpec] = {
    InnerTickKind.MONOLOG: InnerTickKindSpec(
        activity=InnerTickActivity.MONOLOG,
        turn_track=CompanionTurnTrack.INNER_TICK_MONOLOG,
        throttle_kind=InnerTickThrottleKind.MONOLOG,
        chat_history_marker=MONOLOG_INNER_TICK_CHAT_HISTORY_USER_MARKER,
        suppresses_user_delivery=False,
        async_tool_prompt_builder=build_system_messages_for_inner_tick_monolog,
    ),
    InnerTickKind.AUTONOMY: InnerTickKindSpec(
        activity=InnerTickActivity.AUTONOMY,
        turn_track=CompanionTurnTrack.INNER_TICK_AUTONOMY,
        throttle_kind=InnerTickThrottleKind.AUTONOMY,
        chat_history_marker="",
        suppresses_user_delivery=True,
        async_tool_prompt_builder=build_system_messages_for_inner_tick_autonomy,
    ),
    InnerTickKind.PROACTIVE_CHAT: InnerTickKindSpec(
        activity=InnerTickActivity.PROACTIVE_CHAT,
        turn_track=CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT,
        throttle_kind=None,
        chat_history_marker=PROACTIVE_CHAT_TRANSCRIPT_USER_MARKER,
        suppresses_user_delivery=False,
        async_tool_prompt_builder=None,
    ),
    InnerTickKind.SCHEDULED: InnerTickKindSpec(
        activity=InnerTickActivity.PROACTIVE_CHAT,
        turn_track=CompanionTurnTrack.INNER_TICK_SCHEDULED,
        throttle_kind=None,
        chat_history_marker="",
        suppresses_user_delivery=False,
        async_tool_prompt_builder=None,
    ),
}

_INNER_TICK_TRACK_TO_KIND: dict[CompanionTurnTrack, InnerTickKind] = {
    spec.turn_track: kind for kind, spec in INNER_TICK_KINDS.items()
}


def inner_tick_spec(kind: InnerTickKind) -> InnerTickKindSpec:
    """Return the descriptor row for ``kind``."""
    spec = INNER_TICK_KINDS.get(kind)
    assert spec is not None
    return spec


def inner_tick_kind_for_track(
    track: CompanionTurnTrack,
) -> InnerTickKind | None:
    """Map a turn track to its inner-tick kind, or ``None`` for user-facing tracks."""
    return _INNER_TICK_TRACK_TO_KIND.get(track)
