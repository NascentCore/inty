"""Scope scheduled inner-tick fire without presence (#3689)."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.companion_harness.companion.models import CompanionTurnResult
from app.core.companion_harness.companion.schedule_queue import ScheduleTask
from app.core.companion_harness.runtime.inner_tick_fire import InnerTickKernelResult
from app.services.agentic_companion.inner_tick_scope import InnerTickChatResolveMode
from app.services.agentic_companion.scope_inner_tick_fire import (
    try_fire_scheduled_for_scope,
)
from app.services.agentic_companion.session import InnerTickCoords


@dataclass(frozen=True)
class _Resolved:
    user_id: str = "u1"
    agent_id: str = "a1"
    chat_row_id: str = "agent-scope:u1:a1"
    chat_row_agent_id: str = "a1"
    model_override: object = object()


@pytest.mark.asyncio
async def test_try_fire_scheduled_for_scope_no_due_task_returns_false() -> None:
    with (
        patch(
            "app.services.agentic_companion.scope_inner_tick_fire."
            "resolve_inner_tick_scope_coords_for_triple",
            new=AsyncMock(return_value=_Resolved()),
        ),
        patch(
            "app.services.agentic_companion.scope_inner_tick_fire."
            "_scope_kernel_context",
            new=AsyncMock(return_value=(MagicMock(), MagicMock())),
        ),
        patch(
            "app.services.agentic_companion.scope_inner_tick_fire."
            "inner_tick_turn_scope",
        ) as turn_scope,
        patch(
            "app.services.agentic_companion.scope_inner_tick_fire."
            "due_scheduled_task",
            return_value=None,
        ),
    ):
        turn_scope.return_value.__aenter__ = AsyncMock(return_value=None)
        turn_scope.return_value.__aexit__ = AsyncMock(return_value=None)
        fired = await try_fire_scheduled_for_scope(
            coords=InnerTickCoords(
                user_id="u1",
                agent_id="a1",
                chat_id="agent-scope:u1:a1",
            ),
            poll_source="scope_inner_tick_worker",
            chat_resolve_mode=InnerTickChatResolveMode.READ_ONLY,
            implicit_signal_bundle=None,
        )
    assert fired is False


@pytest.mark.asyncio
async def test_try_fire_scheduled_for_scope_delivers_with_none_delivery() -> None:
    due = ScheduleTask(
        id="t1",
        exec_time_utc="2020-01-01T00:00:00+00:00",
        task_text="drink water",
        status="pending",
        created_at_utc="2020-01-01T00:00:00+00:00",
    )
    kernel_result = InnerTickKernelResult(
        turn=CompanionTurnResult(assistant_text="time to drink"),
        track_path="inner_tick_scheduled",
        transcript_user_text="[scheduled: drink water]",
        scheduled_task_id="t1",
        throttle_line_count=None,
        throttle_kind=None,
    )
    deliver_mock = AsyncMock(return_value=True)
    with (
        patch(
            "app.services.agentic_companion.scope_inner_tick_fire."
            "resolve_inner_tick_scope_coords_for_triple",
            new=AsyncMock(return_value=_Resolved()),
        ),
        patch(
            "app.services.agentic_companion.scope_inner_tick_fire."
            "_scope_kernel_context",
            new=AsyncMock(return_value=(MagicMock(), MagicMock())),
        ),
        patch(
            "app.services.agentic_companion.scope_inner_tick_fire."
            "inner_tick_turn_scope",
        ) as turn_scope,
        patch(
            "app.services.agentic_companion.scope_inner_tick_fire."
            "due_scheduled_task",
            return_value=due,
        ),
        patch(
            "app.services.agentic_companion.scope_inner_tick_fire."
            "kernel_fire_scheduled",
            new=AsyncMock(return_value=kernel_result),
        ),
        patch(
            "app.services.agentic_companion.scope_inner_tick_fire."
            "deliver_visible_inner_tick_turn",
            deliver_mock,
        ),
    ):
        turn_scope.return_value.__aenter__ = AsyncMock(return_value=None)
        turn_scope.return_value.__aexit__ = AsyncMock(return_value=None)
        fired = await try_fire_scheduled_for_scope(
            coords=InnerTickCoords(
                user_id="u1",
                agent_id="a1",
                chat_id="agent-scope:u1:a1",
            ),
            poll_source="scope_inner_tick_worker",
            chat_resolve_mode=InnerTickChatResolveMode.READ_ONLY,
            implicit_signal_bundle=None,
        )
    assert fired is True
    deliver_mock.assert_awaited_once()
    call_input = deliver_mock.await_args.args[0]
    assert call_input.delivery is None
    assert call_input.scheduled_task_id == "t1"
