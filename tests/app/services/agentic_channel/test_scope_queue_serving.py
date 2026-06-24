"""Tests for per-scope ScopeQueueServing worker and output pump."""

from __future__ import annotations

import asyncio
from itertools import chain, repeat
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agent_channel.channel_kind import (
    ChannelKind,
)
from app.core.companion_harness.agentic_companion.output_queue import (
    ReadyOutputMessage,
    clear_output_queues_for_tests,
    get_output_queue_for_scope,
)
from app.services.agentic_companion.downlink import DownlinkKind
from app.services.agentic_channel.scope_queue_serving import (
    ScopeDrainCompletion,
    ScopeQueueServing,
)
from app.services.agentic_channel.serving import DrainScopeOnceResult


@pytest.fixture(autouse=True)
def _clear_output_queue_registry() -> None:
    clear_output_queues_for_tests()
    yield
    clear_output_queues_for_tests()


@pytest.mark.asyncio
async def test_scope_serving_delivers_each_output_row_once() -> None:
    """ScopeQueueServing output pump alone delivers each ready row once."""
    scope = AgentScope(user_id="user-once", agent_id="agent-once")
    message_id = "out-once"
    ready = ReadyOutputMessage(
        message_id=message_id,
        batch_id="batch-1",
        kind=DownlinkKind.USER_REPLY,
        text="single bubble",
        sequence=1,
        message_ids=("input-1",),
    )
    queue = get_output_queue_for_scope(scope)
    queue._ready.append(ready)
    deliver_mock = AsyncMock()
    drain_calls = 0

    async def deliver_message(message: ReadyOutputMessage) -> None:
        await deliver_mock(message)

    async def fake_drain(*_args, **_kwargs) -> DrainScopeOnceResult:
        nonlocal drain_calls
        drain_calls += 1
        if drain_calls == 1:
            return DrainScopeOnceResult(
                reply_text=ready.text,
                tool_background_started=False,
                batch_drained=True,
                input_message_ids=("in-1",),
            )
        return DrainScopeOnceResult(
            reply_text="",
            tool_background_started=False,
            batch_drained=False,
            input_message_ids=(),
        )

    serving = ScopeQueueServing(
        scope,
        background_output_sink=None,
        deliver_message=deliver_message,
        on_drain_complete=AsyncMock(),
        runtime_channel=ChannelKind.TELEGRAM,
    )
    with patch(
        "app.core.companion_harness.agentic_companion.output_queue.AsyncSessionLocal"
    ) as session_cls:
        session = AsyncMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        session_cls.return_value = session
        repo = AsyncMock()
        repo.mark_delivered = AsyncMock()
        with patch(
            "app.core.companion_harness.agentic_companion.output_queue.PostgresOutputQueueRepository",
            return_value=repo,
        ):
            with patch(
                "app.services.agentic_channel.scope_queue_serving.drain_scope_once_via_companion",
                side_effect=fake_drain,
            ):
                await serving.start()
                await asyncio.sleep(0.08)
                await serving.stop()

    assert deliver_mock.await_count == 1
    assert deliver_mock.await_args.args[0].message_id == message_id


@pytest.mark.asyncio
async def test_wake_triggers_drain_until_empty() -> None:
    scope = AgentScope(user_id="user-wake", agent_id="agent-wake")
    drain_mock = AsyncMock(
        side_effect=[
            DrainScopeOnceResult(
                reply_text="a",
                tool_background_started=False,
                batch_drained=True,
                input_message_ids=("m1",),
            ),
            DrainScopeOnceResult(
                reply_text="b",
                tool_background_started=False,
                batch_drained=True,
                input_message_ids=("m2",),
            ),
            DrainScopeOnceResult(
                reply_text="",
                tool_background_started=False,
                batch_drained=False,
                input_message_ids=(),
            ),
        ]
    )
    on_complete = AsyncMock()
    serving = ScopeQueueServing(
        scope,
        background_output_sink=None,
        deliver_message=AsyncMock(),
        on_drain_complete=on_complete,
        runtime_channel=ChannelKind.TELEGRAM,
    )
    with patch(
        "app.services.agentic_channel.scope_queue_serving.drain_scope_once_via_companion",
        drain_mock,
    ):
        await serving.start()
        serving.wake(runtime_channel=ChannelKind.TELEGRAM)
        await asyncio.sleep(0.05)
        await serving.stop()

    assert drain_mock.await_count == 3
    on_complete.assert_awaited()
    assert on_complete.await_count == 2


@pytest.mark.asyncio
async def test_drain_failure_does_not_kill_worker() -> None:
    scope = AgentScope(user_id="user-fail", agent_id="agent-fail")
    drain_mock = AsyncMock(
        side_effect=[
            RuntimeError("drain boom"),
            DrainScopeOnceResult(
                reply_text="ok",
                tool_background_started=False,
                batch_drained=True,
                input_message_ids=("m3",),
            ),
            DrainScopeOnceResult(
                reply_text="",
                tool_background_started=False,
                batch_drained=False,
                input_message_ids=(),
            ),
        ]
    )
    serving = ScopeQueueServing(
        scope,
        background_output_sink=None,
        deliver_message=AsyncMock(),
        on_drain_complete=AsyncMock(),
        runtime_channel=ChannelKind.TELEGRAM,
    )
    with patch(
        "app.services.agentic_channel.scope_queue_serving.drain_scope_once_via_companion",
        drain_mock,
    ):
        await serving.start()
        serving.wake(runtime_channel=ChannelKind.TELEGRAM)
        await asyncio.sleep(0.05)
        serving.wake(runtime_channel=ChannelKind.TELEGRAM)
        await asyncio.sleep(0.05)
        await serving.stop()

    assert drain_mock.await_count >= 3


@pytest.mark.asyncio
async def test_tool_background_batch_still_reports_completion() -> None:
    scope = AgentScope(user_id="user-tool-bg", agent_id="agent-tool-bg")
    drain_mock = AsyncMock(
        side_effect=[
            DrainScopeOnceResult(
                reply_text="",
                tool_background_started=True,
                batch_drained=True,
                input_message_ids=("m4", "m5"),
            ),
            DrainScopeOnceResult(
                reply_text="",
                tool_background_started=False,
                batch_drained=False,
                input_message_ids=(),
            ),
        ]
    )
    on_complete = AsyncMock()
    serving = ScopeQueueServing(
        scope,
        background_output_sink=None,
        deliver_message=AsyncMock(),
        on_drain_complete=on_complete,
        runtime_channel=ChannelKind.TELEGRAM,
    )
    with patch(
        "app.services.agentic_channel.scope_queue_serving.drain_scope_once_via_companion",
        drain_mock,
    ):
        await serving.start()
        serving.wake(runtime_channel=ChannelKind.TELEGRAM)
        await asyncio.sleep(0.05)
        await serving.stop()

    on_complete.assert_awaited_once_with(
        ScopeDrainCompletion(
            input_message_ids=("m4", "m5"),
            tool_background_started=True,
        )
    )


@pytest.mark.asyncio
async def test_start_recovers_after_pump_task_exits() -> None:
    scope = AgentScope(user_id="user-restart", agent_id="agent-restart")
    serving = ScopeQueueServing(
        scope,
        background_output_sink=None,
        deliver_message=AsyncMock(),
        on_drain_complete=AsyncMock(),
        runtime_channel=ChannelKind.TELEGRAM,
    )
    with patch(
        "app.services.agentic_channel.scope_queue_serving.drain_scope_once_via_companion",
        new_callable=AsyncMock,
        return_value=DrainScopeOnceResult(
            reply_text="",
            tool_background_started=False,
            batch_drained=False,
            input_message_ids=(),
        ),
    ):
        with patch(
            "app.services.agentic_channel.scope_queue_serving.channel_output_pump",
            new_callable=AsyncMock,
            side_effect=RuntimeError("pump exited"),
        ) as pump_mock:
            await serving.start()
            await asyncio.sleep(0.05)
            await serving.start()
            await asyncio.sleep(0.05)
            await serving.stop()

    assert pump_mock.await_count == 2


@pytest.mark.asyncio
async def test_stop_cancels_input_and_pump_tasks() -> None:
    scope = AgentScope(user_id="user-stop", agent_id="agent-stop")
    serving = ScopeQueueServing(
        scope,
        background_output_sink=None,
        deliver_message=AsyncMock(),
        on_drain_complete=AsyncMock(),
        runtime_channel=ChannelKind.TELEGRAM,
    )
    with patch(
        "app.services.agentic_channel.scope_queue_serving.drain_scope_once_via_companion",
        new_callable=AsyncMock,
        return_value=DrainScopeOnceResult(
            reply_text="",
            tool_background_started=False,
            batch_drained=False,
            input_message_ids=(),
        ),
    ):
        with patch(
            "app.services.agentic_channel.scope_queue_serving.channel_output_pump",
            new_callable=AsyncMock,
        ) as pump_mock:
            await serving.start()
            assert serving._input_task is not None
            assert serving._pump_task is not None
            await serving.stop()
            pump_mock.assert_awaited_once()
    assert serving._input_task is None
    assert serving._pump_task is None


@pytest.mark.asyncio
async def test_output_pump_delivers_via_deliver_message() -> None:
    scope = AgentScope(user_id="user-pump", agent_id="agent-pump")
    sent: list[str] = []

    async def deliver_message(message: ReadyOutputMessage) -> None:
        sent.append(message.text)

    ready = ReadyOutputMessage(
        message_id="out-1",
        batch_id="batch-1",
        kind=DownlinkKind.USER_REPLY,
        text="pumped reply",
        sequence=1,
        message_ids=("input-1",),
    )

    fake_queue = MagicMock()
    fake_queue.pull_ready_batch = AsyncMock(
        side_effect=chain([[ready]], repeat([])),
    )
    fake_queue.ack_delivered = AsyncMock()
    stop = asyncio.Event()
    with patch(
        "app.services.agentic_channel.serving.get_output_queue_for_scope",
        return_value=fake_queue,
    ):
        from app.services.agentic_channel.serving import channel_output_pump

        task = asyncio.create_task(
            channel_output_pump(
                scope, deliver_message=deliver_message, stop_event=stop
            )
        )
        await asyncio.sleep(0.05)
        stop.set()
        await task

    assert sent == ["pumped reply"]
    fake_queue.ack_delivered.assert_awaited()


@pytest.mark.asyncio
async def test_output_pump_marks_delivery_failure_retryable() -> None:
    scope = AgentScope(user_id="user-pump-fail", agent_id="agent-pump-fail")

    async def deliver_message(_message: ReadyOutputMessage) -> None:
        raise RuntimeError("send failed")

    ready = ReadyOutputMessage(
        message_id="out-2",
        batch_id="batch-1",
        kind=DownlinkKind.USER_REPLY,
        text="will retry",
        sequence=1,
        message_ids=("input-1",),
    )

    fake_queue = MagicMock()
    fake_queue.pull_ready_batch = AsyncMock(
        side_effect=chain([[ready]], repeat([])),
    )
    fake_queue.ack_delivered = AsyncMock()
    fake_queue.mark_delivery_failed = AsyncMock()
    stop = asyncio.Event()
    with patch(
        "app.services.agentic_channel.serving.get_output_queue_for_scope",
        return_value=fake_queue,
    ):
        from app.services.agentic_channel.serving import channel_output_pump

        task = asyncio.create_task(
            channel_output_pump(
                scope, deliver_message=deliver_message, stop_event=stop
            )
        )
        await asyncio.sleep(0.05)
        stop.set()
        await task

    fake_queue.ack_delivered.assert_not_awaited()
    fake_queue.mark_delivery_failed.assert_awaited_once()


@pytest.mark.asyncio
async def test_output_pump_claims_after_wake_sets_runtime_channel() -> None:
    scope = AgentScope(user_id="user-pump-wake", agent_id="agent-pump-wake")
    deliver_mock = AsyncMock()
    serving = ScopeQueueServing(
        scope,
        background_output_sink=None,
        deliver_message=deliver_mock,
        on_drain_complete=AsyncMock(),
        runtime_channel=ChannelKind.APP_WS,
    )
    fake_queue = MagicMock()
    fake_queue.pull_ready_batch = AsyncMock(return_value=())
    fake_queue.ack_delivered = AsyncMock()
    stop = asyncio.Event()
    with patch(
        "app.services.agentic_channel.scope_queue_serving.channel_output_pump",
        new_callable=AsyncMock,
    ) as pump_mock:
        with patch(
            "app.services.agentic_channel.serving.get_output_queue_for_scope",
            return_value=fake_queue,
        ):
            await serving.start()
            await asyncio.sleep(0.02)
            serving.wake(runtime_channel=ChannelKind.APP_WS)
            await asyncio.sleep(0.02)
            stop.set()
            await serving.stop()

    _, kwargs = pump_mock.await_args
    assert kwargs.get("resolve_delivery_target") is not None
    channel, wire_id = serving._resolve_output_delivery_target()
    assert channel == ChannelKind.APP_WS
    assert wire_id == f"app_ws:{scope.registry_key()}"


@pytest.mark.asyncio
async def test_drain_on_start_uses_constructor_runtime_channel() -> None:
    scope = AgentScope(user_id="user-start-drain", agent_id="agent-start-drain")
    drain_mock = AsyncMock(
        return_value=DrainScopeOnceResult(
            reply_text="",
            tool_background_started=False,
            batch_drained=False,
            input_message_ids=(),
        )
    )
    serving = ScopeQueueServing(
        scope,
        background_output_sink=None,
        deliver_message=AsyncMock(),
        on_drain_complete=AsyncMock(),
        runtime_channel=ChannelKind.TELEGRAM,
    )
    with patch(
        "app.services.agentic_channel.scope_queue_serving.drain_scope_once_via_companion",
        drain_mock,
    ):
        await serving.start()
        await asyncio.sleep(0.05)
        await serving.stop()

    drain_mock.assert_awaited()
    assert drain_mock.await_args.kwargs["runtime_channel"] == (
        ChannelKind.TELEGRAM
    )
