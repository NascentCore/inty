"""Tests for harness runtime inner-tick due checks and kernel fire helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.companion_harness.companion.inner_tick_kind import InnerTickKind
from app.core.companion_harness.agentic_companion.types import UserMessageBatch
from app.core.companion_harness.companion.models import (
    CompanionTurnResult,
    InnerTickThrottleKind,
    MONOLOG_INNER_TICK_CHAT_HISTORY_USER_MARKER,
)
from app.core.companion_harness.runtime.inner_tick_fire import (
    InnerTickKernelInput,
    InnerTickThrottleSnapshot,
    inner_tick_remain_seconds,
    kernel_fire_throttled,
    proactive_chat_remain_seconds,
)


def test_proactive_chat_remain_seconds_returns_non_negative() -> None:
    throttle = InnerTickThrottleSnapshot(
        last_monolog_monotonic=None,
        last_monolog_line_count=None,
        last_autonomy_monotonic=None,
        last_autonomy_line_count=None,
    )
    assert throttle.last_monolog_line_count is None
    assert (
        proactive_chat_remain_seconds.__name__
        == "proactive_chat_remain_seconds"
    )
    assert inner_tick_remain_seconds.__name__ == "inner_tick_remain_seconds"


def test_inner_tick_remain_seconds_uses_kind_specific_throttle_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_next_inner_tick_wait_seconds(
        mem_store: object,
        *,
        last_inner_fire_monotonic: object,
        last_monolog_transcript_line_count: object,
        overrides: object,
    ) -> float:
        captured["last_inner_fire_monotonic"] = last_inner_fire_monotonic
        captured["last_monolog_transcript_line_count"] = (
            last_monolog_transcript_line_count
        )
        return 12.5

    monkeypatch.setattr(
        "app.core.companion_harness.runtime.inner_tick_fire.next_inner_tick_wait_seconds",
        fake_next_inner_tick_wait_seconds,
    )
    throttle = InnerTickThrottleSnapshot(
        last_monolog_monotonic=1.0,
        last_monolog_line_count=7,
        last_autonomy_monotonic=2.0,
        last_autonomy_line_count=9,
    )
    mem_store = MagicMock()

    assert (
        inner_tick_remain_seconds(
            InnerTickKind.MONOLOG,
            mem_store,
            throttle,
        )
        == 12.5
    )
    assert captured["last_inner_fire_monotonic"] == 1.0
    assert captured["last_monolog_transcript_line_count"] == 7

    captured.clear()
    assert (
        inner_tick_remain_seconds(
            InnerTickKind.AUTONOMY,
            mem_store,
            throttle,
        )
        == 12.5
    )
    assert captured["last_inner_fire_monotonic"] == 2.0
    assert captured["last_monolog_transcript_line_count"] == 9


@pytest.mark.asyncio
async def test_kernel_fire_throttled_monolog_result_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    companion_turn = CompanionTurnResult(
        assistant_text="",
        tool_background_started=False,
    )
    manager = MagicMock()
    manager.run_inner_tick_monolog_turn = AsyncMock(return_value=companion_turn)
    kernel_input = InnerTickKernelInput(
        manager=manager,
        session=MagicMock(),
        mem_store=MagicMock(),
        throttle=InnerTickThrottleSnapshot(
            last_monolog_monotonic=None,
            last_monolog_line_count=None,
            last_autonomy_monotonic=None,
            last_autonomy_line_count=None,
        ),
        runtime_context=MagicMock(),
        preset_user_msg_uuid="preset-1",
        agentic_output_queue=MagicMock(),
        user_message_batch=UserMessageBatch(
            batch_id="agent-initiated:inner_tick:preset-1",
            message_ids=("preset-1",),
        ),
    )
    monkeypatch.setattr(
        "app.core.companion_harness.runtime.inner_tick_fire.monolog_transcript_line_count",
        lambda _store: 42,
    )

    result = await kernel_fire_throttled(InnerTickKind.MONOLOG, kernel_input)

    assert result.track_path == "inner_tick_monolog"
    assert (
        result.transcript_user_text
        == MONOLOG_INNER_TICK_CHAT_HISTORY_USER_MARKER
    )
    assert result.throttle_kind == InnerTickThrottleKind.MONOLOG
    assert result.throttle_line_count == 42
    assert result.scheduled_task_id is None


@pytest.mark.asyncio
async def test_kernel_fire_throttled_autonomy_result_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    companion_turn = CompanionTurnResult(
        assistant_text="",
        tool_background_started=True,
    )
    manager = MagicMock()
    manager.run_inner_tick_autonomy_turn = AsyncMock(
        return_value=companion_turn
    )
    kernel_input = InnerTickKernelInput(
        manager=manager,
        session=MagicMock(),
        mem_store=MagicMock(),
        throttle=InnerTickThrottleSnapshot(
            last_monolog_monotonic=None,
            last_monolog_line_count=None,
            last_autonomy_monotonic=None,
            last_autonomy_line_count=None,
        ),
        runtime_context=MagicMock(),
        preset_user_msg_uuid="preset-2",
        agentic_output_queue=MagicMock(),
        user_message_batch=UserMessageBatch(
            batch_id="agent-initiated:inner_tick:preset-2",
            message_ids=("preset-2",),
        ),
    )
    monkeypatch.setattr(
        "app.core.companion_harness.runtime.inner_tick_fire.monolog_transcript_line_count",
        lambda _store: 99,
    )

    result = await kernel_fire_throttled(InnerTickKind.AUTONOMY, kernel_input)

    assert result.track_path == "inner_tick_autonomy"
    assert result.transcript_user_text == ""
    assert result.throttle_kind == InnerTickThrottleKind.AUTONOMY
    assert result.throttle_line_count == 99
