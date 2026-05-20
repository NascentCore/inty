"""Track entry functions fix inner-tick / implicit-sign-on flags before ``run_turn``."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.utils.config import CompanionMemoryBootstrapType

from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    CompanionTurnResult,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.turn_tracks import (
    run_companion_implicit_sign_on_greeting_turn,
    run_companion_inner_tick_maintenance_turn,
    run_companion_inner_tick_proactive_chat_turn,
    run_companion_inner_tick_scheduled_turn,
    run_companion_user_chat_turn,
)
from app.schemas.implicit_signals import ImplicitSignalBundle


def _minimal_turn_kwargs() -> dict[str, object]:
    return {
        "store": MagicMock(),
        "llm_client": MagicMock(),
        "defer_memory_update": True,
        "memory_config": None,
        "transcript_compaction": None,
        "transcript_llm_window_max_messages": None,
        "repository_only_store_text": True,
        "memory_bootstrap_type": "NONE",
        "background_output_sink": None,
        "preset_user_msg_uuid": None,
        "implicit_signal_bundle": None,
        "langsmith_parent_run_enabled": False,
        "tool_bg_idle_event": None,
    }


@pytest.mark.asyncio
async def test_user_chat_track_passes_non_inner_tick_flags(tmp_path) -> None:
    scope = CompanionScope("turn-tracks-daily", "agent", tmp_path.name)
    st = MemoryStore(scope=scope, repository=None)
    st.write_document(
        "context.json",
        json.dumps(
            {
                "context_mode": "public",
                "user_id": "u",
                "companion_id": "a",
                "chat_id": "c",
                "workspace_bootstrap_user_interactive_completed": True,
            },
            ensure_ascii=False,
        )
        + "\n",
    )
    for rel in ("IDENTITY.md", "SOUL.md", "USER.md", "MEMORY.md"):
        st.write_document(rel, f"{rel}\n")
    stub = CompanionTurnResult(
        trace_id="t",
        user_msg_uuid="u",
        assistant_text="",
    )
    kwargs = _minimal_turn_kwargs()
    kwargs["store"] = st
    kwargs["memory_bootstrap_type"] = (
        CompanionMemoryBootstrapType.USER_INTERACTIVE.value
    )
    with patch(
        "app.core.companion_harness.companion.turn._run_companion_turn_core",
        new_callable=AsyncMock,
        return_value=stub,
    ) as run_turn_mock:
        await run_companion_user_chat_turn("hello", **kwargs)
    assert run_turn_mock.await_args is not None
    assert run_turn_mock.await_args.args[0] == "hello"
    assert run_turn_mock.await_args.kwargs["track"] == CompanionTurnTrack.USER_CHAT


@pytest.mark.asyncio
async def test_user_chat_turn_selects_bootstrap_track_when_incomplete(
    tmp_path,
) -> None:
    scope = CompanionScope("turn-tracks", "agent", tmp_path.name)
    st = MemoryStore(scope=scope, repository=None)
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
    for rel in ("IDENTITY.md", "SOUL.md", "USER.md", "MEMORY.md"):
        st.write_document(rel, f"{rel}\n")
    stub = CompanionTurnResult(
        trace_id="t",
        user_msg_uuid="u",
        assistant_text="",
    )
    kwargs = _minimal_turn_kwargs()
    kwargs["store"] = st
    kwargs["memory_bootstrap_type"] = (
        CompanionMemoryBootstrapType.USER_INTERACTIVE.value
    )
    with patch(
        "app.core.companion_harness.companion.turn._run_companion_turn_core",
        new_callable=AsyncMock,
        return_value=stub,
    ) as run_turn_mock:
        await run_companion_user_chat_turn("hello", **kwargs)
    assert run_turn_mock.await_args is not None
    assert (
        run_turn_mock.await_args.kwargs["track"]
        == CompanionTurnTrack.USER_CHAT_BOOTSTRAP
    )


@pytest.mark.asyncio
async def test_user_chat_track_rejects_implicit_sign_on_bundle() -> None:
    bundle = ImplicitSignalBundle(user_signed_on=True)
    kwargs = _minimal_turn_kwargs()
    kwargs["implicit_signal_bundle"] = bundle
    with pytest.raises(ValueError, match="implicit sign-on"):
        await run_companion_user_chat_turn("hello", **kwargs)


@pytest.mark.asyncio
async def test_implicit_sign_on_track() -> None:
    bundle = ImplicitSignalBundle(user_signed_on=True)
    stub = CompanionTurnResult(
        trace_id="t",
        user_msg_uuid="u",
        assistant_text="",
    )
    with patch(
        "app.core.companion_harness.companion.turn._run_companion_turn_core",
        new_callable=AsyncMock,
        return_value=stub,
    ) as run_turn_mock:
        kwargs = _minimal_turn_kwargs()
        kwargs["implicit_signal_bundle"] = bundle
        await run_companion_implicit_sign_on_greeting_turn("hi", **kwargs)
    assert run_turn_mock.await_args is not None
    assert (
        run_turn_mock.await_args.kwargs["track"]
        == CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING
    )
    assert run_turn_mock.await_args.kwargs["implicit_signal_bundle"] is bundle


@pytest.mark.asyncio
async def test_proactive_inner_tick_track() -> None:
    stub = CompanionTurnResult(
        trace_id="t",
        user_msg_uuid="u",
        assistant_text="",
    )
    with patch(
        "app.core.companion_harness.companion.turn._run_companion_turn_core",
        new_callable=AsyncMock,
        return_value=stub,
    ) as run_turn_mock:
        await run_companion_inner_tick_proactive_chat_turn(**_minimal_turn_kwargs())
    assert run_turn_mock.await_args is not None
    assert run_turn_mock.await_args.args[0] == ""
    assert (
        run_turn_mock.await_args.kwargs["track"]
        == CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT
    )


@pytest.mark.asyncio
async def test_scheduled_inner_tick_track() -> None:
    stub = CompanionTurnResult(
        trace_id="t",
        user_msg_uuid="u",
        assistant_text="",
    )
    scheduled_text = "（定时提醒触发）提醒事项：喝水"
    with patch(
        "app.core.companion_harness.companion.turn._run_companion_turn_core",
        new_callable=AsyncMock,
        return_value=stub,
    ) as run_turn_mock:
        await run_companion_inner_tick_scheduled_turn(
            scheduled_text,
            **_minimal_turn_kwargs(),
        )
    assert run_turn_mock.await_args is not None
    assert run_turn_mock.await_args.args[0] == scheduled_text
    assert (
        run_turn_mock.await_args.kwargs["track"]
        == CompanionTurnTrack.INNER_TICK_SCHEDULED
    )


@pytest.mark.asyncio
async def test_maintenance_inner_tick_track() -> None:
    stub = CompanionTurnResult(
        trace_id="t",
        user_msg_uuid="u",
        assistant_text="",
    )
    with patch(
        "app.core.companion_harness.companion.turn._run_companion_turn_core",
        new_callable=AsyncMock,
        return_value=stub,
    ) as run_turn_mock:
        await run_companion_inner_tick_maintenance_turn(**_minimal_turn_kwargs())
    assert run_turn_mock.await_args is not None
    assert (
        run_turn_mock.await_args.kwargs["track"]
        == CompanionTurnTrack.INNER_TICK_MAINTENANCE
    )
