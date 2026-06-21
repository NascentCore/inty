"""CompanionManager track methods forward kwargs without duplicate keyword errors."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.llms.client import CompanionLLMConfig, CompanionLLMClient
from app.core.companion_harness.companion.manager import (
    CompanionConfig,
    CompanionManager,
)
from app.core.companion_harness.companion.models import CompanionTurnResult
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from app.schemas.implicit_signals import ImplicitSignalBundle


def _minimal_manager_session() -> MagicMock:
    session = MagicMock()
    session.store = MagicMock()
    session.llm_client = MagicMock()
    session.config = CompanionConfig(llm=CompanionLLMConfig(api_key="k"))
    session.tool_bg_idle = None
    return session


@pytest.mark.asyncio
async def test_manager_implicit_sign_on_greeting_forwards_implicit_signal_bundle() -> (
    None
):
    bundle = ImplicitSignalBundle(user_signed_on=True)
    stub = CompanionTurnResult(
        trace_id="t",
        user_msg_uuid="u",
        assistant_text="",
    )
    manager = CompanionManager(
        CompanionConfig(llm=CompanionLLMConfig(api_key="k"))
    )
    session = _minimal_manager_session()

    with patch(
        "app.core.companion_harness.companion.manager.run_companion_implicit_sign_on_greeting_turn",
        new_callable=AsyncMock,
        return_value=stub,
    ) as track_mock:
        result = await manager.run_implicit_sign_on_greeting_turn(
            session,
            "hi",
            runtime_context=TurnRuntimeContext(
                channel=CompanionRuntimeChannel.APP,
                implicit_signal_bundle=bundle,
            ),
        )

    assert result is stub
    assert track_mock.await_args is not None
    assert track_mock.await_args.args[0] == "hi"
    assert (
        track_mock.await_args.kwargs[
            "deps"
        ].runtime_context.implicit_signal_bundle
        is bundle
    )
    assert (
        track_mock.await_args.kwargs["deps"].bootstrap_interim_output_sink
        is None
    )


@pytest.mark.asyncio
async def test_manager_turns_do_not_serialize_without_dreaming() -> None:
    start_gate = asyncio.Event()
    release_gate = asyncio.Event()
    manager = CompanionManager(
        CompanionConfig(llm=CompanionLLMConfig(api_key="k"))
    )
    session = _minimal_manager_session()
    entered = 0

    async def _track_turn(
        *args: object, **kwargs: object
    ) -> CompanionTurnResult:
        nonlocal entered
        entered += 1
        if entered == 2:
            start_gate.set()
        await release_gate.wait()
        return CompanionTurnResult(
            trace_id="t",
            user_msg_uuid="u",
            assistant_text="",
        )

    with patch(
        "app.core.companion_harness.companion.manager.run_companion_implicit_sign_on_greeting_turn",
        side_effect=_track_turn,
    ):
        task_a = asyncio.create_task(
            manager.run_implicit_sign_on_greeting_turn(session, "a")
        )
        task_b = asyncio.create_task(
            manager.run_implicit_sign_on_greeting_turn(session, "b")
        )
        await asyncio.wait_for(start_gate.wait(), timeout=1.0)
        release_gate.set()
        await asyncio.gather(task_a, task_b)

    assert entered == 2


def test_companion_manager_accepts_injected_llm_client() -> None:
    config = CompanionConfig(llm=CompanionLLMConfig(api_key="k"))
    injected = CompanionLLMClient(config.llm)
    manager = CompanionManager(config, llm_client=injected)
    assert manager._llm_client is injected  # noqa: SLF001
