"""Track entry functions fix inner-tick / implicit-sign-on flags before core turn."""

from __future__ import annotations

import json
from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.utils.config import CompanionMemoryBootstrapType

from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    CompanionTurnResult,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.turn import (
    run_companion_implicit_sign_on_greeting_turn,
    run_companion_inner_tick_maintenance_turn,
    run_companion_inner_tick_proactive_chat_turn,
    run_companion_inner_tick_scheduled_turn,
    run_companion_user_chat_turn,
    run_inner_tick_autonomy,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.turn_deps import CompanionTurnDeps
from app.schemas.implicit_signals import ImplicitSignalBundle


def _minimal_turn_deps(**overrides: object) -> CompanionTurnDeps:
    deps = CompanionTurnDeps(
        store=MagicMock(),
        llm_client=MagicMock(),
        transcript_compaction=None,
        transcript_llm_window_max_messages=None,
        repository_only_store_text=True,
        memory_bootstrap_type="NONE",
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
        background_output_sink=None,
        preset_user_msg_uuid=None,
        langsmith_parent_run_enabled=False,
        tool_bg_idle_event=None,
        bootstrap_interim_output_sink=None,
    )
    if overrides:
        return replace(deps, **overrides)
    return deps


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
    deps = _minimal_turn_deps(
        store=st,
        memory_bootstrap_type=CompanionMemoryBootstrapType.USER_INTERACTIVE.value,
    )
    with patch(
        "app.core.companion_harness.companion.turn._run_companion_turn_core",
        new_callable=AsyncMock,
        return_value=stub,
    ) as run_turn_mock:
        await run_companion_user_chat_turn("hello", deps=deps)
    assert run_turn_mock.await_args is not None
    assert run_turn_mock.await_args.args[0] == "hello"
    assert (
        run_turn_mock.await_args.kwargs["track"] == CompanionTurnTrack.USER_CHAT
    )


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
                "context_mode": "unspecific",
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
    deps = _minimal_turn_deps(
        store=st,
        memory_bootstrap_type=CompanionMemoryBootstrapType.USER_INTERACTIVE.value,
    )
    with patch(
        "app.core.companion_harness.companion.turn._run_companion_turn_core",
        new_callable=AsyncMock,
        return_value=stub,
    ) as run_turn_mock:
        await run_companion_user_chat_turn("hello", deps=deps)
    assert run_turn_mock.await_args is not None
    assert (
        run_turn_mock.await_args.kwargs["track"]
        == CompanionTurnTrack.USER_CHAT_BOOTSTRAP
    )


@pytest.mark.asyncio
async def test_user_chat_turn_plumbs_agentic_output_queue_for_bootstrap(
    tmp_path,
) -> None:
    scope = CompanionScope("turn-tracks-queue", "agent", tmp_path.name)
    st = MemoryStore(scope=scope, repository=None)
    st.write_document(
        "context.json",
        json.dumps(
            {
                "context_mode": "unspecific",
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
    from tests.app.core.companion_harness.companion.bootstrap_test_helpers import (
        bootstrap_queue_turn_deps,
    )
    from tests.app.core.companion_harness.companion.companion_scripted_llm import (
        companion_llm_client_with_scripted_transport,
        scripted_harness_llm_config,
    )
    from app.external_services.fakes.openai import fake_step_text

    client, _ = companion_llm_client_with_scripted_transport(
        scripted_harness_llm_config(),
        (fake_step_text("final"),),
    )
    deps = bootstrap_queue_turn_deps(st, client)
    stub = CompanionTurnResult(
        trace_id="t",
        user_msg_uuid="u",
        assistant_text="final",
    )
    with patch(
        "app.core.companion_harness.companion.turn._run_companion_turn_core",
        new_callable=AsyncMock,
        return_value=stub,
    ) as run_turn_mock:
        await run_companion_user_chat_turn("hello", deps=deps)
    assert run_turn_mock.await_args is not None
    passed_deps = run_turn_mock.await_args.kwargs["deps"]
    assert passed_deps.agentic_output_queue is deps.agentic_output_queue
    assert passed_deps.user_message_batch is deps.user_message_batch


@pytest.mark.asyncio
async def test_user_chat_track_rejects_implicit_sign_on_bundle() -> None:
    bundle = ImplicitSignalBundle(user_signed_on=True)
    deps = _minimal_turn_deps(
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=bundle,
        ),
    )
    with pytest.raises(ValueError, match="implicit sign-on"):
        await run_companion_user_chat_turn("hello", deps=deps)


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
        deps = _minimal_turn_deps(
            runtime_context=TurnRuntimeContext(
                channel=ChannelKind.APP_WS,
                implicit_signal_bundle=bundle,
            ),
        )
        await run_companion_implicit_sign_on_greeting_turn("hi", deps=deps)
    assert run_turn_mock.await_args is not None
    assert (
        run_turn_mock.await_args.kwargs["track"]
        == CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING
    )
    assert (
        run_turn_mock.await_args.kwargs[
            "deps"
        ].runtime_context.implicit_signal_bundle
        is bundle
    )


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
        await run_companion_inner_tick_proactive_chat_turn(
            deps=_minimal_turn_deps()
        )
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
            deps=_minimal_turn_deps(),
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
        await run_companion_inner_tick_maintenance_turn(
            deps=_minimal_turn_deps()
        )
    assert run_turn_mock.await_args is not None
    assert (
        run_turn_mock.await_args.kwargs["track"]
        == CompanionTurnTrack.INNER_TICK_MAINTENANCE
    )


@pytest.mark.asyncio
async def test_autonomy_inner_tick_track_forwards_runtime_context() -> None:
    stub = CompanionTurnResult(
        trace_id="t",
        user_msg_uuid="u",
        assistant_text="",
    )
    bundle = ImplicitSignalBundle(user_signed_on=True)
    deps = _minimal_turn_deps(
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=bundle,
        ),
    )
    with patch(
        "app.core.companion_harness.companion.turn._run_companion_turn_core",
        new_callable=AsyncMock,
        return_value=stub,
    ) as run_turn_mock:
        await run_inner_tick_autonomy(deps=deps)
    assert run_turn_mock.await_args is not None
    assert run_turn_mock.await_args.args[0] == ""
    assert (
        run_turn_mock.await_args.kwargs["track"]
        == CompanionTurnTrack.INNER_TICK_AUTONOMY
    )
    forwarded_deps = run_turn_mock.await_args.kwargs["deps"]
    assert forwarded_deps.runtime_context.implicit_signal_bundle is bundle
