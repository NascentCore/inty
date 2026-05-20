"""``CompanionTurnTrack`` maps to route_mode and legacy flag translation."""

from __future__ import annotations

import json

from app.utils.config import CompanionMemoryBootstrapType

from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    load_context_meta,
    load_prompt_bundle,
)
from app.core.companion_harness.companion.prompt_stack import (
    companion_turn_tools_and_system_messages,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.turn_track import (
    track_from_legacy_flags,
    turn_flags_for_track,
)
from app.core.companion_harness.companion.turn_routes import TurnRouteMode
from app.core.companion_harness.companion.models import InnerTickActivity
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.schemas.implicit_signals import ImplicitSignalBundle


def test_track_from_legacy_flags() -> None:
    sign_on = ImplicitSignalBundle(user_signed_on=True)
    assert (
        track_from_legacy_flags(
            inner_tick_turn=False,
            inner_tick_activity=InnerTickActivity.MAINTENANCE,
            implicit_signal_bundle=sign_on,
        )
        == CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING
    )
    assert (
        track_from_legacy_flags(
            inner_tick_turn=True,
            inner_tick_activity=InnerTickActivity.PROACTIVE_CHAT,
            implicit_signal_bundle=None,
        )
        == CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT
    )
    assert (
        track_from_legacy_flags(
            inner_tick_turn=True,
            inner_tick_activity=InnerTickActivity.MAINTENANCE,
            implicit_signal_bundle=None,
        )
        == CompanionTurnTrack.INNER_TICK_MAINTENANCE
    )
    assert (
        track_from_legacy_flags(
            inner_tick_turn=False,
            inner_tick_activity=InnerTickActivity.MAINTENANCE,
            implicit_signal_bundle=None,
        )
        == CompanionTurnTrack.USER_CHAT
    )


def test_turn_flags_for_track() -> None:
    assert turn_flags_for_track(CompanionTurnTrack.USER_CHAT) == (
        False,
        InnerTickActivity.MAINTENANCE,
    )
    assert turn_flags_for_track(CompanionTurnTrack.USER_CHAT_BOOTSTRAP) == (
        False,
        InnerTickActivity.MAINTENANCE,
    )
    assert turn_flags_for_track(CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT) == (
        True,
        InnerTickActivity.PROACTIVE_CHAT,
    )


def test_track_route_mode_matrix(tmp_path) -> None:
    scope = CompanionScope("track-route", "agent", tmp_path.name)
    st = MemoryStore(scope=scope, repository=None)
    for rel, body in (
        ("IDENTITY.md", "id\n"),
        ("SOUL.md", "soul\n"),
        ("USER.md", "user\n"),
        ("MEMORY.md", "mem\n"),
    ):
        st.write_document(rel, body)
    st.write_document(
        "context.json",
        json.dumps(
            {
                "context_mode": "public",
                "user_id": "u",
                "companion_id": "a",
                "chat_id": "c",
            },
            ensure_ascii=False,
        )
        + "\n",
    )
    context = load_context_meta(store=st)
    bundle = load_prompt_bundle(st, meta=context)
    mb = CompanionMemoryBootstrapType.NONE.value

    _, _, user_route = companion_turn_tools_and_system_messages(
        store=st,
        bundle=bundle,
        context=context,
        memory_bootstrap_type=mb,
        track=CompanionTurnTrack.USER_CHAT,
    )
    assert user_route == TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL

    _, _, implicit_route = companion_turn_tools_and_system_messages(
        store=st,
        bundle=bundle,
        context=context,
        memory_bootstrap_type=mb,
        track=CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING,
    )
    assert implicit_route == TurnRouteMode.CHAT_ONLY_SYNC

    _, _, proactive_route = companion_turn_tools_and_system_messages(
        store=st,
        bundle=bundle,
        context=context,
        memory_bootstrap_type=mb,
        track=CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT,
    )
    assert proactive_route == TurnRouteMode.PROACTIVE_CHAT_SYNC


def test_bootstrap_track_tools_and_system(tmp_path) -> None:
    scope = CompanionScope("track-bootstrap", "agent", tmp_path.name)
    st = MemoryStore(scope=scope, repository=None)
    for rel, body in (
        ("IDENTITY.md", "id\n"),
        ("SOUL.md", "soul\n"),
        ("USER.md", "user\n"),
        ("MEMORY.md", "mem\n"),
    ):
        st.write_document(rel, body)
    st.write_document(
        "context.json",
        json.dumps(
            {
                "context_mode": "bootstrap",
                "user_id": "u",
                "companion_id": "a",
                "chat_id": "c",
                "workspace_bootstrap_user_interactive_completed": False,
            },
            ensure_ascii=False,
        )
        + "\n",
    )
    context = load_context_meta(store=st)
    bundle = load_prompt_bundle(st, meta=context)
    mb = CompanionMemoryBootstrapType.USER_INTERACTIVE.value
    tools, systems, route = companion_turn_tools_and_system_messages(
        store=st,
        bundle=bundle,
        context=context,
        memory_bootstrap_type=mb,
        track=CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
    )
    tool_names = sorted(t["function"]["name"] for t in tools)
    assert tool_names == [
        "companion_bootstrap_user_interactive_complete",
        "companion_update_prompt_slice",
    ]
    joined = "\n".join(
        str(m.get("content") or "")
        for m in systems
        if m.get("role") == "system"
    )
    assert "INTERACTIVE_BOOTSTRAP" in joined
    assert route == TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL
