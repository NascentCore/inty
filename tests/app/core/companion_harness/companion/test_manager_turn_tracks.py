"""CompanionManager track methods forward kwargs without duplicate keyword errors."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.companion_harness.companion.llm_client import CompanionLLMConfig
from app.core.companion_harness.companion.manager import CompanionConfig, CompanionManager
from app.core.companion_harness.companion.models import CompanionTurnResult
from app.schemas.implicit_signals import ImplicitSignalBundle


def _minimal_manager_session() -> MagicMock:
    session = MagicMock()
    session.store = MagicMock()
    session.llm_client = MagicMock()
    session.config = CompanionConfig(llm=CompanionLLMConfig(api_key="k"))
    session.tool_bg_idle = None
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
            implicit_signal_bundle=bundle,
        )

    assert result is stub
    assert track_mock.await_args is not None
    assert track_mock.await_args.args[0] == "hi"
    assert track_mock.await_args.kwargs["implicit_signal_bundle"] is bundle
    assert "bootstrap_interim_output_sink" not in track_mock.await_args.kwargs

