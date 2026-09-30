"""Tests for ``TRACK_POLICY`` and ``build_loop_execution_policy``."""

from __future__ import annotations

import pytest

from app.core.companion_harness.companion.inner_tick_kind import (
    inner_tick_kind_for_track,
    inner_tick_spec,
)
from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    InnerTickActivity,
)
from app.core.companion_harness.companion.turn_pipeline import (
    resolve_turn_runtime_flags,
)
from app.core.companion_harness.llm.langsmith_invocation_extra import (
    LangsmithLlmSource,
)
from app.core.companion_harness.loop.track_policy import (
    TRACK_POLICY,
    CompanionLlmScene,
    build_loop_execution_policy,
)
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY,
)


def test_track_policy_covers_all_companion_turn_tracks() -> None:
    assert set(TRACK_POLICY) == set(CompanionTurnTrack)


@pytest.mark.parametrize("track", list(CompanionTurnTrack))
def test_track_policy_row_exists(track: CompanionTurnTrack) -> None:
    assert TRACK_POLICY[track] is not None


def test_proactive_chat_policy_high_reasoning_and_chat_scene() -> None:
    policy = TRACK_POLICY[CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT]
    assert policy.high_reasoning is True
    assert policy.llm_scene == CompanionLlmScene.CHAT


def test_monolog_policy_empty_write_allowlist() -> None:
    policy = TRACK_POLICY[CompanionTurnTrack.INNER_TICK_MONOLOG]
    assert policy.write_allowlist == frozenset()
    assert policy.uses_in_turn_tool_loop is True


def test_autonomy_policy_allowlist() -> None:
    policy = TRACK_POLICY[CompanionTurnTrack.INNER_TICK_AUTONOMY]
    assert (
        policy.write_allowlist == MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY
    )
    assert policy.write_allowlist == frozenset(
        {DEFAULT_MEMORY_STORE_SCOPE_PATHS.life_currents_md}
    )


def test_bootstrap_policy_foreground_source() -> None:
    policy = TRACK_POLICY[CompanionTurnTrack.USER_CHAT_BOOTSTRAP]
    assert policy.foreground_source == LangsmithLlmSource.BOOTSTRAP_TRACK


def test_scheduled_policy_inner_tick_scene() -> None:
    policy = TRACK_POLICY[CompanionTurnTrack.INNER_TICK_SCHEDULED]
    assert policy.llm_scene == CompanionLlmScene.INNER_TICK


@pytest.mark.parametrize("track", list(CompanionTurnTrack))
def test_build_loop_execution_policy_covers_all_tracks(
    track: CompanionTurnTrack,
) -> None:
    runtime_flags = resolve_turn_runtime_flags(
        track=track,
        user_text="hello",
        implicit_signal_bundle=None,
    )
    execution = build_loop_execution_policy(
        track=track,
        runtime_flags=runtime_flags,
        has_openai_tools=True,
    )
    assert execution is not None


def test_autonomy_execution_suppresses_delivery_and_skips_tool_bg_routing() -> (
    None
):
    runtime_flags = resolve_turn_runtime_flags(
        track=CompanionTurnTrack.INNER_TICK_AUTONOMY,
        user_text="",
        implicit_signal_bundle=None,
    )
    execution = build_loop_execution_policy(
        track=CompanionTurnTrack.INNER_TICK_AUTONOMY,
        runtime_flags=runtime_flags,
        has_openai_tools=True,
    )
    assert execution.suppresses_user_delivery is True
    assert execution.skip_tool_bg_finish_routing is True
    assert execution.tool_bg_activity_label == InnerTickActivity.AUTONOMY.value


def test_user_chat_execution_no_tool_bg_activity_label() -> None:
    runtime_flags = resolve_turn_runtime_flags(
        track=CompanionTurnTrack.USER_CHAT,
        user_text="hi",
        implicit_signal_bundle=None,
    )
    execution = build_loop_execution_policy(
        track=CompanionTurnTrack.USER_CHAT,
        runtime_flags=runtime_flags,
        has_openai_tools=True,
    )
    assert execution.tool_bg_activity_label is None
    assert execution.suppresses_user_delivery is False


def test_greeting_execution_zero_tool_rounds_without_tools() -> None:
    runtime_flags = resolve_turn_runtime_flags(
        track=CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING,
        user_text="",
        implicit_signal_bundle=None,
    )
    execution = build_loop_execution_policy(
        track=CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING,
        runtime_flags=runtime_flags,
        has_openai_tools=False,
    )
    assert execution.max_tool_call_rounds == 0


@pytest.mark.parametrize(
    "track",
    [
        CompanionTurnTrack.INNER_TICK_MONOLOG,
        CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT,
        CompanionTurnTrack.INNER_TICK_SCHEDULED,
        CompanionTurnTrack.INNER_TICK_AUTONOMY,
    ],
)
def test_inner_tick_execution_matches_inner_tick_kind_registry(
    track: CompanionTurnTrack,
) -> None:
    kind = inner_tick_kind_for_track(track)
    assert kind is not None
    spec = inner_tick_spec(kind)
    runtime_flags = resolve_turn_runtime_flags(
        track=track,
        user_text=(
            "scheduled text"
            if track == CompanionTurnTrack.INNER_TICK_SCHEDULED
            else ""
        ),
        implicit_signal_bundle=None,
    )
    execution = build_loop_execution_policy(
        track=track,
        runtime_flags=runtime_flags,
        has_openai_tools=True,
    )
    assert execution.tool_bg_activity_label == spec.activity.value
    assert execution.suppresses_user_delivery == spec.suppresses_user_delivery
