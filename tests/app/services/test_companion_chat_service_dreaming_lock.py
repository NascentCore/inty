from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.core.companion_harness.companion.manager import CompanionActivityGate
from app.core.companion_harness.companion.dreaming import DreamingCandidate
from app.core.companion_harness.companion.models import ChatMessage
from app.services.agentic_companion.inner_tick_fire import _inner_tick_turn_scope
from app.services import companion_chat_service


def _session_and_model() -> tuple[MagicMock, MagicMock, MagicMock]:
    session = MagicMock()
    session.is_initialized = True
    session.activity_gate = CompanionActivityGate()
    manager = MagicMock()
    manager.get_or_create_session.return_value = session
    model = MagicMock()
    model.id_on_provider = "chat-model"
    return session, manager, model


def _dreaming_candidate() -> DreamingCandidate:
    now = datetime.now(timezone.utc)
    return DreamingCandidate(
        rows=[
            ChatMessage(
                role="user",
                content="hi",
                ts=now.isoformat(),
                uuid="u",
            )
        ],
        latest_user_ts=now,
        boundary_line_count=1,
        boundary_uuid="u",
    )


def test_run_companion_dreaming_skips_gate_when_not_due() -> None:
    session, manager, model = _session_and_model()
    result_box: dict[str, bool] = {}

    def _dreaming_due(*args: object, **kwargs: object) -> None:
        assert not session.activity_gate.dreaming_active()
        return None

    def _run() -> None:
        result_box["result"] = companion_chat_service.run_companion_dreaming_for_api(
            user_id="u",
            agent_id="a",
            chat_id="c",
            resolved_chat_model=model,
            dreaming_idle_seconds=120,
        )

    with (
        patch(
            "app.services.companion_chat_service._companion_tool_model_api_id",
            return_value="tool-model",
        ),
        patch(
            "app.services.companion_chat_service._companion_manager_for_resolved_model",
            return_value=manager,
        ),
        patch(
            "app.services.companion_chat_service.dreaming_due",
            side_effect=_dreaming_due,
        ),
        patch(
            "app.services.companion_chat_service.memory_update_after_dreaming"
        ) as memory_update,
    ):
        _run()

    assert result_box["result"] is False
    memory_update.assert_not_called()
    assert not session.activity_gate.dreaming_active()


def test_run_companion_dreaming_holds_activity_gate_for_update() -> None:
    session, manager, model = _session_and_model()
    result_box: dict[str, bool] = {}

    def _memory_update(*args: object, **kwargs: object) -> None:
        assert session.activity_gate.dreaming_active()

    def _run() -> None:
        result_box["result"] = companion_chat_service.run_companion_dreaming_for_api(
            user_id="u",
            agent_id="a",
            chat_id="c",
            resolved_chat_model=model,
            dreaming_idle_seconds=120,
        )

    with (
        patch(
            "app.services.companion_chat_service._companion_tool_model_api_id",
            return_value="tool-model",
        ),
        patch(
            "app.services.companion_chat_service._companion_manager_for_resolved_model",
            return_value=manager,
        ),
        patch(
            "app.services.companion_chat_service.dreaming_due",
            return_value=_dreaming_candidate(),
        ),
        patch(
            "app.services.companion_chat_service.memory_update_after_dreaming",
            side_effect=_memory_update,
        ),
        patch(
            "app.services.companion_chat_service.dreaming_race_guard_matches",
            return_value=False,
        ),
    ):
        _run()

    assert result_box["result"] is False
    assert not session.activity_gate.dreaming_active()


def test_run_companion_dreaming_saves_checkpoint_after_update() -> None:
    session, manager, model = _session_and_model()
    result_box: dict[str, bool] = {}

    def _memory_update(*args: object, **kwargs: object) -> None:
        assert session.activity_gate.dreaming_active()

    def _run() -> None:
        result_box["result"] = companion_chat_service.run_companion_dreaming_for_api(
            user_id="u",
            agent_id="a",
            chat_id="c",
            resolved_chat_model=model,
            dreaming_idle_seconds=120,
        )

    with (
        patch(
            "app.services.companion_chat_service._companion_tool_model_api_id",
            return_value="tool-model",
        ),
        patch(
            "app.services.companion_chat_service._companion_manager_for_resolved_model",
            return_value=manager,
        ),
        patch(
            "app.services.companion_chat_service.dreaming_due",
            return_value=_dreaming_candidate(),
        ),
        patch(
            "app.services.companion_chat_service.memory_update_after_dreaming",
            side_effect=_memory_update,
        ) as memory_update,
        patch(
            "app.services.companion_chat_service.dreaming_race_guard_matches",
            return_value=True,
        ),
        patch(
            "app.services.companion_chat_service.save_dreaming_state"
        ) as save_dreaming_state,
    ):
        _run()

    assert result_box["result"] is True
    memory_update.assert_called_once()
    save_dreaming_state.assert_called_once()
    assert not session.activity_gate.dreaming_active()


def test_companion_session_dreaming_active_reads_session_gate() -> None:
    session, manager, model = _session_and_model()
    session.activity_gate.enter_dreaming()

    try:
        with (
            patch(
                "app.services.companion_chat_service._companion_tool_model_api_id",
                return_value="tool-model",
            ),
            patch(
                "app.services.companion_chat_service._companion_manager_for_resolved_model",
                return_value=manager,
            ),
        ):
            assert companion_chat_service.companion_session_dreaming_active(
                user_id="u",
                agent_id="a",
                chat_id="c",
                resolved_chat_model=model,
            )
    finally:
        session.activity_gate.exit_dreaming()


@pytest.mark.asyncio
async def test_inner_tick_turn_scope_skips_when_dreaming_is_active() -> None:
    _, _, model = _session_and_model()
    coordinator = MagicMock()
    coordinator.turn_lock = asyncio.Lock()

    with patch(
        "app.services.companion_chat_service.companion_session_dreaming_active",
        return_value=True,
    ) as dreaming_active:
        async with _inner_tick_turn_scope(
            coordinator=coordinator,
            label="companion_ws_maintenance_inner_tick",
            user_id="u",
            agent_id="a",
            chat_id="c",
            resolved_chat_model=model,
            ws_conn_id="ws",
        ) as proceed:
            assert not proceed

    dreaming_active.assert_called_once_with(
        user_id="u",
        agent_id="a",
        chat_id="c",
        resolved_chat_model=model,
    )
