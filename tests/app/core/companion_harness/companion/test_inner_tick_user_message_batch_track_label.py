"""Inner-tick ``UserMessageBatch`` must carry track-specific batch ids (#3401).

Generated entirely by Cursor agent.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.companion_harness.companion.manager import (
    CompanionConfig,
    CompanionManager,
)
from app.core.companion_harness.companion.models import (
    CompanionTurnResult,
    CompanionTurnTrack,
)
from app.core.llms.client import CompanionLLMConfig


def _minimal_manager_session() -> MagicMock:
    session = MagicMock()
    session.store = MagicMock()
    session.store.scope = MagicMock()
    session.store.scope.user_id = "user-1"
    session.store.scope.companion_id = "agent-1"
    session.llm_client = MagicMock()
    session.config = CompanionConfig(llm=CompanionLLMConfig(api_key="k"))
    session.tool_bg_idle = None
    return session


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("manager_method", "track_run_patch", "track_label"),
    [
        (
            "run_inner_tick_scheduled_turn",
            "run_companion_inner_tick_scheduled_turn",
            CompanionTurnTrack.INNER_TICK_SCHEDULED.value,
        ),
        (
            "run_inner_tick_proactive_chat_turn",
            "run_companion_inner_tick_proactive_chat_turn",
            CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT.value,
        ),
        (
            "run_inner_tick_monolog_turn",
            "run_companion_inner_tick_monolog_turn",
            CompanionTurnTrack.INNER_TICK_MONOLOG.value,
        ),
        (
            "run_inner_tick_autonomy_turn",
            "run_inner_tick_autonomy",
            CompanionTurnTrack.INNER_TICK_AUTONOMY.value,
        ),
    ],
)
async def test_inner_tick_manager_turn_synthesizes_track_specific_user_message_batch(
    manager_method: str,
    track_run_patch: str,
    track_label: str,
) -> None:
    """Manager entry is the single synthesis point: preset uuid + concrete track label."""
    preset_uid = "preset-inner-tick-uuid"

    manager = CompanionManager(
        CompanionConfig(llm=CompanionLLMConfig(api_key="k"))
    )
    session = _minimal_manager_session()
    stub = CompanionTurnResult(
        trace_id="t",
        user_msg_uuid=preset_uid,
        assistant_text="",
    )

    with patch(
        f"app.core.companion_harness.companion.manager.{track_run_patch}",
        new_callable=AsyncMock,
        return_value=stub,
    ) as track_mock:
        run_turn = getattr(manager, manager_method)
        if manager_method == "run_inner_tick_scheduled_turn":
            await run_turn(
                session,
                "scheduled reminder text",
                preset_user_msg_uuid=preset_uid,
            )
        else:
            await run_turn(
                session,
                preset_user_msg_uuid=preset_uid,
            )

    deps = track_mock.await_args.kwargs["deps"]
    assert deps.user_message_batch is not None
    assert deps.user_message_batch.batch_id == (
        f"agent-initiated:{track_label}:{preset_uid}"
    )
    assert deps.user_message_batch.message_ids == (preset_uid,)
