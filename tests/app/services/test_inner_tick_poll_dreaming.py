from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.services.agentic_companion import inner_tick_poll
from app.services.agentic_companion.inner_tick_delivery import InnerTickDelivery


def _poll_delivery() -> InnerTickDelivery:
    return InnerTickDelivery(
        ws_outbound_queue=asyncio.Queue(),
        weixin_assistant_text=None,
        runtime_channel=CompanionRuntimeChannel.APP,
    )


@pytest.mark.asyncio
async def test_run_inner_tick_poll_skips_all_actions_when_dreaming() -> None:
    ctx = {"user_id": "u", "agent_id": "a", "chat_id": "c"}
    coordinator = MagicMock()
    subscription_svc = MagicMock()
    feats = MagicMock()

    with (
        patch(
            "app.services.agentic_companion.inner_tick_poll._inner_tick_poll_skipped_by_dreaming",
            new_callable=AsyncMock,
            return_value=True,
        ) as skipped,
        patch.object(
            inner_tick_poll.inner_tick_fire,
            "try_fire_scheduled_inner_tick",
            new_callable=AsyncMock,
        ) as scheduled,
        patch.object(
            inner_tick_poll.inner_tick_fire,
            "try_fire_proactive_chat_inner_tick",
            new_callable=AsyncMock,
        ) as proactive,
        patch.object(
            inner_tick_poll.inner_tick_fire,
            "try_fire_maintenance_inner_tick",
            new_callable=AsyncMock,
        ) as maintenance,
        patch(
            "app.services.agentic_companion.inner_tick_poll.global_config_loaded_from_config_yaml"
        ) as cfg,
    ):
        cfg.app.features = feats
        await inner_tick_poll.run_inner_tick_poll(
            ctx=ctx,
            delivery=_poll_delivery(),
            subscription_svc=subscription_svc,
            coordinator=coordinator,
            ws_conn_id="ws",
            tc_box=[None],
        )

    skipped.assert_awaited_once()
    scheduled.assert_not_awaited()
    proactive.assert_not_awaited()
    maintenance.assert_not_awaited()


@pytest.mark.asyncio
async def test_inner_tick_poll_skipped_by_dreaming_reads_session_gate() -> None:
    ctx = {"user_id": "u", "agent_id": "a", "chat_id": "c"}
    subscription_svc = MagicMock()
    subscription_svc.get_user_current_subscription = AsyncMock(
        return_value=MagicMock()
    )
    current_user = MagicMock()
    chat = MagicMock()
    chat.id = "c"
    model = MagicMock()
    model.id_on_provider = "chat-model"

    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = current_user
    mock_db.execute = AsyncMock(return_value=mock_result)

    class _DbCtx:
        async def __aenter__(self) -> MagicMock:
            return mock_db

        async def __aexit__(self, *args: object) -> None:
            return None

    with (
        patch(
            "app.services.agentic_companion.inner_tick_poll.AsyncSessionLocal",
            return_value=_DbCtx(),
        ),
        patch(
            "app.services.agentic_companion.inner_tick_poll.chat_service.get_or_create_chat_by_agent",
            new_callable=AsyncMock,
            return_value=chat,
        ),
        patch(
            "app.services.agentic_companion.inner_tick_poll.select_chat_model",
            return_value=model,
        ),
        patch(
            "app.services.agentic_companion.inner_tick_poll.companion_chat_service.companion_session_dreaming_active",
            return_value=True,
        ) as dreaming_active,
    ):
        skipped = await inner_tick_poll._inner_tick_poll_skipped_by_dreaming(
            ctx=ctx,
            subscription_svc=subscription_svc,
            ws_conn_id="ws",
        )

    assert skipped
    dreaming_active.assert_called_once_with(
        user_id="u",
        agent_id="a",
        chat_id="c",
        resolved_chat_model=model,
    )
