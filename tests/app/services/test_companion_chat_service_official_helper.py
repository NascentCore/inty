from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1.endpoints.chat import _companion_ai_meta_from_turn_result
from app.core.companion_harness.companion.models import (
    CompanionIdentity,
    CompanionTurnResult,
)
from app.core.companion_harness.memory.memory_registry import (
    shutdown_all_memory_stores,
)
from app.schemas.chat_websocket import ChatWsCompanionWireMessageMetaData
from app.services import companion_chat_service
from app.utils.models_catalog import resolve_chat_text_model
from tests.app.core.companion_harness.companion_memory_registry_dsn import (
    companion_memory_registry_dsn,
)


@pytest.mark.asyncio
async def test_run_user_chat_uses_companion_turn_when_dreaming_active() -> None:
    """User chat does not short-circuit to official helper while dreaming."""
    companion_memory_registry_dsn()
    resolved_model = resolve_chat_text_model("deepseek/deepseek-v4-flash")
    expected = CompanionTurnResult(
        assistant_text="hey",
        user_msg_uuid="550e8400-e29b-41d4-a716-446655440000",
        assistant_msg_uuid="33333333-3333-4333-8333-000000000002",
        trace_id="trace-1",
    )
    _, session, _, _, _ = await companion_chat_service._companion_session_for_api_turn(
        user_id="u",
        agent_id="a",
        chat_id="c",
        resolved_chat_model=resolved_model,
        session_id=None,
    )
    session.activity_gate.enter_dreaming()
    try:
        with patch.object(
            companion_chat_service.CompanionManager,
            "run_user_chat_turn",
            new_callable=AsyncMock,
            return_value=expected,
        ) as run_turn:
            out = await companion_chat_service.run_user_chat(
                user_id="u",
                agent_id="a",
                chat_id="c",
                user_text="hi",
                resolved_chat_model=resolved_model,
                companion_identity=CompanionIdentity(display_name="Luna"),
                preset_user_msg_uuid="550e8400-e29b-41d4-a716-446655440000",
            )
    finally:
        session.activity_gate.exit_dreaming()
        shutdown_all_memory_stores()

    run_turn.assert_awaited_once()
    assert out is expected
    assert out.assistant_source == "chat"


def test_companion_ai_meta_includes_official_helper_reason() -> None:
    turn = CompanionTurnResult(
        assistant_text="Luna is sleeping ~",
        assistant_source="official_helper",
        official_helper_reason="dreaming",
        user_msg_uuid="550e8400-e29b-41d4-a716-446655440000",
        assistant_msg_uuid="33333333-3333-4333-8333-000000000002",
        trace_id="trace-1",
    )
    meta = _companion_ai_meta_from_turn_result(turn)
    assert meta["source"] == "official_helper"
    assert meta["officialHelperReason"] == "dreaming"


def test_chat_ws_companion_wire_meta_accepts_official_helper() -> None:
    meta = ChatWsCompanionWireMessageMetaData.model_validate(
        {
            "source": "official_helper",
            "officialHelperReason": "dreaming",
            "user_msg_uuid": "550e8400-e29b-41d4-a716-446655440000",
        }
    )
    assert meta.source == "official_helper"
    assert meta.official_helper_reason == "dreaming"
