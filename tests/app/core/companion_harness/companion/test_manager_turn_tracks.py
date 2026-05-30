"""CompanionManager track methods forward kwargs without duplicate keyword errors."""

from __future__ import annotations

import asyncio
import threading
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.companion_harness.companion.llm_client import CompanionLLMConfig
from app.core.companion_harness.companion.manager import (
    CompanionActivityGate,
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
    session.activity_gate = CompanionActivityGate()
    return session


@pytest.mark.asyncio
async def test_manager_implicit_sign_on_greeting_forwards_implicit_signal_bundle() -> None:
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
        track_mock.await_args.kwargs["runtime_context"].implicit_signal_bundle
        is bundle
    )
    assert "bootstrap_interim_output_sink" not in track_mock.await_args.kwargs


@pytest.mark.asyncio
async def test_manager_turn_waits_when_dreaming_is_active() -> None:
    stub = CompanionTurnResult(
        trace_id="t",
        user_msg_uuid="u",
        assistant_text="",
    )
    manager = CompanionManager(
        CompanionConfig(llm=CompanionLLMConfig(api_key="k"))
    )
    session = _minimal_manager_session()
    session.activity_gate.enter_dreaming()

    with patch(
        "app.core.companion_harness.companion.manager.run_companion_implicit_sign_on_greeting_turn",
        new_callable=AsyncMock,
        return_value=stub,
    ) as track_mock:
        task = asyncio.create_task(
            manager.run_implicit_sign_on_greeting_turn(session, "hi")
        )
        await asyncio.sleep(0.05)
        assert track_mock.await_count == 0
        session.activity_gate.exit_dreaming()
        result = await asyncio.wait_for(task, timeout=1.0)

    assert result is stub
    assert track_mock.await_count == 1


@pytest.mark.asyncio
async def test_cancelled_turn_waiting_for_dreaming_does_not_enter_activity() -> None:
    stub = CompanionTurnResult(
        trace_id="t",
        user_msg_uuid="u",
        assistant_text="",
    )
    manager = CompanionManager(
        CompanionConfig(llm=CompanionLLMConfig(api_key="k"))
    )
    session = _minimal_manager_session()
    session.activity_gate.enter_dreaming()

    with patch(
        "app.core.companion_harness.companion.manager.run_companion_implicit_sign_on_greeting_turn",
        new_callable=AsyncMock,
        return_value=stub,
    ) as track_mock:
        task = asyncio.create_task(
            manager.run_implicit_sign_on_greeting_turn(session, "hi")
        )
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=1.0)
        session.activity_gate.exit_dreaming()
        await asyncio.sleep(0.1)

    dreaming_reentered = threading.Event()

    def _enter_dreaming_again() -> None:
        session.activity_gate.enter_dreaming()
        dreaming_reentered.set()

    dreaming_thread = threading.Thread(target=_enter_dreaming_again)
    dreaming_thread.start()
    assert dreaming_reentered.wait(timeout=1.0)
    session.activity_gate.exit_dreaming()
    dreaming_thread.join(timeout=1.0)
    assert track_mock.await_count == 0


@pytest.mark.asyncio
async def test_manager_turns_do_not_serialize_without_dreaming() -> None:
    start_gate = asyncio.Event()
    release_gate = asyncio.Event()
    manager = CompanionManager(
        CompanionConfig(llm=CompanionLLMConfig(api_key="k"))
    )
    session = _minimal_manager_session()
    entered = 0

    async def _track_turn(*args: object, **kwargs: object) -> CompanionTurnResult:
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


@pytest.mark.asyncio
async def test_dreaming_waits_for_active_turn_and_blocks_new_turns() -> None:
    release_first_turn = asyncio.Event()
    first_turn_started = asyncio.Event()
    dreaming_entered = asyncio.Event()
    manager = CompanionManager(
        CompanionConfig(llm=CompanionLLMConfig(api_key="k"))
    )
    session = _minimal_manager_session()
    calls: list[str] = []

    async def _track_turn(
        user_text: str, *args: object, **kwargs: object
    ) -> CompanionTurnResult:
        calls.append(user_text)
        if user_text == "first":
            first_turn_started.set()
            await release_first_turn.wait()
        return CompanionTurnResult(
            trace_id="t",
            user_msg_uuid="u",
            assistant_text="",
        )

    def _start_dreaming() -> None:
        session.activity_gate.enter_dreaming()
        dreaming_entered.set()

    with patch(
        "app.core.companion_harness.companion.manager.run_companion_implicit_sign_on_greeting_turn",
        side_effect=_track_turn,
    ):
        first_task = asyncio.create_task(
            manager.run_implicit_sign_on_greeting_turn(session, "first")
        )
        await asyncio.wait_for(first_turn_started.wait(), timeout=1.0)
        dreaming_task = asyncio.create_task(asyncio.to_thread(_start_dreaming))
        await asyncio.sleep(0.05)
        second_task = asyncio.create_task(
            manager.run_implicit_sign_on_greeting_turn(session, "second")
        )
        await asyncio.sleep(0.05)
        assert calls == ["first"]
        release_first_turn.set()
        await asyncio.wait_for(dreaming_entered.wait(), timeout=1.0)
        assert calls == ["first"]
        session.activity_gate.exit_dreaming()
        await asyncio.wait_for(second_task, timeout=1.0)
        await first_task
        await dreaming_task

    assert calls == ["first", "second"]

