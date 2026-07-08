"""Per-track static execution policy for ``AgenticLoop``.

``TRACK_POLICY`` is the loop-layer 1:1 table keyed by ``CompanionTurnTrack``.
``build_loop_execution_policy`` merges it with ``inner_tick_kind`` and turn-prep
runtime flags at plugin build time into ``LoopExecutionPolicy`` on context.
TODO(#3401): merge registries when loop and turn-prep share one track descriptor.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.core.companion_harness.companion.inner_tick_kind import (
    inner_tick_kind_for_track,
    inner_tick_spec,
)
from app.core.companion_harness.companion.in_turn_sync_tool_loop import (
    BOOTSTRAP_SYNC_MAX_TOOL_ROUNDS,
)
from app.core.companion_harness.companion.models import CompanionTurnTrack
from app.core.companion_harness.companion.turn_pipeline import (
    CompanionTurnRuntimeFlags,
)
from app.core.companion_harness.llm.langsmith_invocation_extra import (
    LangsmithLlmSource,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
)


class CompanionLlmScene(StrEnum):
    """Foreground LLM routing scene for one companion turn track."""

    CHAT = "chat"
    INNER_TICK = "inner_tick"


@dataclass(frozen=True)
class TrackPolicy:
    """One static policy row for loop execution knobs on a production track.

    Indexed exclusively via ``TRACK_POLICY``; does not carry prompt text,
    inner-tick identity, or per-turn mutable runtime state.
    """

    high_reasoning: bool
    skip_foreground_envelope: bool
    write_allowlist: frozenset[str]
    uses_in_turn_tool_loop: bool
    max_tool_rounds: int
    llm_scene: CompanionLlmScene
    foreground_source: LangsmithLlmSource


@dataclass(frozen=True)
class LoopExecutionPolicy:
    """Resolved per-turn execution knobs; built before AgenticLoop, consumed as-is."""

    high_reasoning: bool
    skip_foreground_envelope: bool
    write_allowlist: frozenset[str]
    suppresses_user_delivery: bool
    max_tool_call_rounds: int
    llm_scene: CompanionLlmScene
    foreground_source: LangsmithLlmSource
    skip_tool_bg_finish_routing: bool
    tool_bg_activity_label: str | None


_DEFAULT_ALLOWLIST = MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST
_BOOTSTRAP_ALLOWLIST = MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP
_AUTONOMY_ALLOWLIST = MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY
_SYNC_TOOL_ROUNDS = BOOTSTRAP_SYNC_MAX_TOOL_ROUNDS

TRACK_POLICY: dict[CompanionTurnTrack, TrackPolicy] = {
    CompanionTurnTrack.USER_CHAT_BOOTSTRAP: TrackPolicy(
        high_reasoning=False,
        skip_foreground_envelope=False,
        write_allowlist=_BOOTSTRAP_ALLOWLIST,
        uses_in_turn_tool_loop=True,
        max_tool_rounds=_SYNC_TOOL_ROUNDS,
        llm_scene=CompanionLlmScene.CHAT,
        foreground_source=LangsmithLlmSource.BOOTSTRAP_TRACK,
    ),
    CompanionTurnTrack.USER_CHAT: TrackPolicy(
        high_reasoning=False,
        skip_foreground_envelope=False,
        write_allowlist=_DEFAULT_ALLOWLIST,
        uses_in_turn_tool_loop=True,
        max_tool_rounds=_SYNC_TOOL_ROUNDS,
        llm_scene=CompanionLlmScene.CHAT,
        foreground_source=LangsmithLlmSource.SINGLE_COMPLETION,
    ),
    CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING: TrackPolicy(
        high_reasoning=False,
        skip_foreground_envelope=False,
        write_allowlist=_DEFAULT_ALLOWLIST,
        uses_in_turn_tool_loop=False,
        max_tool_rounds=0,
        llm_scene=CompanionLlmScene.CHAT,
        foreground_source=LangsmithLlmSource.IMPLICIT_SIGN_ON_GREETING,
    ),
    CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT: TrackPolicy(
        high_reasoning=True,
        skip_foreground_envelope=False,
        write_allowlist=_DEFAULT_ALLOWLIST,
        uses_in_turn_tool_loop=False,
        max_tool_rounds=0,
        llm_scene=CompanionLlmScene.CHAT,
        foreground_source=LangsmithLlmSource.SINGLE_COMPLETION,
    ),
    CompanionTurnTrack.INNER_TICK_SCHEDULED: TrackPolicy(
        high_reasoning=False,
        skip_foreground_envelope=False,
        write_allowlist=_DEFAULT_ALLOWLIST,
        uses_in_turn_tool_loop=False,
        max_tool_rounds=0,
        llm_scene=CompanionLlmScene.INNER_TICK,
        foreground_source=LangsmithLlmSource.SINGLE_COMPLETION,
    ),
    CompanionTurnTrack.INNER_TICK_MONOLOG: TrackPolicy(
        high_reasoning=False,
        skip_foreground_envelope=False,
        write_allowlist=frozenset(),
        uses_in_turn_tool_loop=True,
        max_tool_rounds=_SYNC_TOOL_ROUNDS,
        llm_scene=CompanionLlmScene.INNER_TICK,
        foreground_source=LangsmithLlmSource.SINGLE_COMPLETION,
    ),
    CompanionTurnTrack.INNER_TICK_AUTONOMY: TrackPolicy(
        high_reasoning=False,
        skip_foreground_envelope=False,
        write_allowlist=_AUTONOMY_ALLOWLIST,
        uses_in_turn_tool_loop=True,
        max_tool_rounds=_SYNC_TOOL_ROUNDS,
        llm_scene=CompanionLlmScene.INNER_TICK,
        foreground_source=LangsmithLlmSource.SINGLE_COMPLETION,
    ),
}

assert set(TRACK_POLICY) == set(CompanionTurnTrack)


def build_loop_execution_policy(
    *,
    track: CompanionTurnTrack,
    runtime_flags: CompanionTurnRuntimeFlags,
    has_openai_tools: bool,
) -> LoopExecutionPolicy:
    """Merge slim ``TRACK_POLICY`` row with runtime_flags / inner_tick_kind at build time."""
    row = TRACK_POLICY[track]
    max_tool_call_rounds = (
        0
        if not row.uses_in_turn_tool_loop or not has_openai_tools
        else row.max_tool_rounds
    )
    kind = inner_tick_kind_for_track(track)
    suppresses_user_delivery = (
        inner_tick_spec(kind).suppresses_user_delivery
        if kind is not None
        else False
    )
    tool_bg_activity_label = (
        runtime_flags.route_inner_activity.value
        if runtime_flags.inner_tick_turn
        else None
    )
    return LoopExecutionPolicy(
        high_reasoning=row.high_reasoning,
        skip_foreground_envelope=row.skip_foreground_envelope,
        write_allowlist=row.write_allowlist,
        suppresses_user_delivery=suppresses_user_delivery,
        max_tool_call_rounds=max_tool_call_rounds,
        llm_scene=row.llm_scene,
        foreground_source=row.foreground_source,
        skip_tool_bg_finish_routing=suppresses_user_delivery,
        tool_bg_activity_label=tool_bg_activity_label,
    )
