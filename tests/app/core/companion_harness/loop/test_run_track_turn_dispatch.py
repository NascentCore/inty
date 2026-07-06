"""Dispatch tests for ``AgenticLoop.run_track_turn`` mechanism routing."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.companion_harness.loop.agentic_loop import AgenticLoop
from app.core.companion_harness.loop.config import AgenticLoopMechanism
from app.core.companion_harness.loop.context import (
    AgenticLoopContext,
    AgenticLoopOutput,
)


@pytest.mark.asyncio
async def test_run_track_turn_dispatches_single_llm() -> None:
    loop = AgenticLoop(
        store=MagicMock(),
        llm_client=MagicMock(),
        legacy_llm_client=MagicMock(),
    )
    expected = AgenticLoopOutput(
        assistant_text="hi",
        significance_meta=None,
        turn_recall=None,
        langsmith_trace_id="t",
        langsmith_run_id="r",
        skip_final_transcript_assistant_row=False,
        tool_background_started=False,
        last_interim_assistant_msg_uuid=None,
        output_message_ids=(),
    )
    with patch.object(
        loop,
        "_run_single_llm_turn",
        new=AsyncMock(return_value=expected),
    ) as single_mock:
        with patch.object(
            loop, "_run_dual_llm_turn", new=AsyncMock()
        ) as dual_mock:
            context = MagicMock(spec=AgenticLoopContext)
            out = await loop.run_track_turn(
                mechanism=AgenticLoopMechanism.SINGLE_LLM,
                context=context,
            )
    assert out is expected
    single_mock.assert_awaited_once_with(context=context)
    dual_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_track_turn_dispatches_dual_llm() -> None:
    loop = AgenticLoop(
        store=MagicMock(),
        llm_client=MagicMock(),
        legacy_llm_client=MagicMock(),
    )
    expected = AgenticLoopOutput(
        assistant_text="hi",
        significance_meta={"importance_round": 5},
        turn_recall="brief",
        langsmith_trace_id="t",
        langsmith_run_id="r",
        skip_final_transcript_assistant_row=False,
        tool_background_started=False,
        last_interim_assistant_msg_uuid=None,
        output_message_ids=("msg-1",),
    )
    with patch.object(
        loop, "_run_single_llm_turn", new=AsyncMock()
    ) as single_mock:
        with patch.object(
            loop,
            "_run_dual_llm_turn",
            new=AsyncMock(return_value=expected),
        ) as dual_mock:
            context = MagicMock(spec=AgenticLoopContext)
            out = await loop.run_track_turn(
                mechanism=AgenticLoopMechanism.DUAL_LLM,
                context=context,
            )
    assert out is expected
    dual_mock.assert_awaited_once_with(context=context)
    single_mock.assert_not_awaited()
