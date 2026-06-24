"""Regression and acceptance tests for sign-on greeting OutputQueue → IM delivery."""

from __future__ import annotations

import asyncio
import json
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.error import HTTPError

import pytest

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.output_queue import (
    OutputDeliveryUnroutableError,
    ReadyOutputMessage,
    clear_output_queues_for_tests,
    ready_output_is_agent_initiated_visible,
)
from app.core.companion_harness.companion.models import (
    CompanionTurnResult,
)
from app.core.companion_harness.agent_channel.gateway import GatewayKind
from app.external_services.telegram_bot_api import TelegramBotApi
from app.services.agentic_channel.adapters.telegram import (
    TelegramChannelAdapter,
)
from app.services.agentic_channel.channel_runtime import (
    ChannelRuntimeState,
    clear_registries_for_tests,
    get_scope_channel_registry,
)
from app.services.agentic_channel.presence import (
    AgentChannelPresence,
    clear_presences_for_tests,
)
from app.services.agentic_channel.serving import (
    _deliver_ready_message,
    flush_scope_output_queue_ready,
)
from app.services.agentic_companion.downlink import DownlinkKind


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _telegram_api_with_sent_capture() -> tuple[TelegramBotApi, list[str]]:
    sent: list[str] = []

    def _capture_urlopen(request, timeout=15):
        if request.full_url.endswith("/sendMessage"):
            sent.append(request.data.decode("utf-8"))
            return _FakeResponse({"ok": True, "result": {}})
        raise HTTPError(
            request.full_url, 404, "not found", hdrs=None, fp=BytesIO()
        )

    api = TelegramBotApi(
        bot_token="greet-delivery-token", urlopen=_capture_urlopen
    )
    return api, sent


def _wire_telegram_active_channel(
    scope: AgentScope,
    *,
    api: TelegramBotApi,
    channel_address: str,
) -> TelegramChannelAdapter:
    adapter = TelegramChannelAdapter(api=api, channel_address=channel_address)
    registry = get_scope_channel_registry(scope)
    registry.states[GatewayKind.TELEGRAM] = ChannelRuntimeState.ACTIVE
    registry.adapters[GatewayKind.TELEGRAM] = adapter
    registry.downlinks[GatewayKind.TELEGRAM] = adapter.as_downlink()
    return adapter


def _wire_app_ws_active_channel(
    scope: AgentScope,
    *,
    outbound: asyncio.Queue,
) -> None:
    from app.services.agentic_channel.adapters.app_ws import AppWsChannelAdapter

    adapter = AppWsChannelAdapter(scope=scope, outbound_queue=outbound)
    registry = get_scope_channel_registry(scope)
    registry.states[GatewayKind.APP_WS] = ChannelRuntimeState.ACTIVE
    registry.adapters[GatewayKind.APP_WS] = adapter
    registry.downlinks[GatewayKind.APP_WS] = adapter.as_downlink()


def _agent_initiated_greeting_message(
    *, kind: DownlinkKind
) -> ReadyOutputMessage:
    return ReadyOutputMessage(
        message_id="out-greet-1",
        batch_id="agent-initiated:test",
        kind=kind,
        text="Hello from Inty.",
        sequence=1,
        message_ids=(),
    )


@pytest.fixture(autouse=True)
def _clear_channel_state() -> None:
    clear_presences_for_tests()
    clear_registries_for_tests()
    clear_output_queues_for_tests()
    yield
    clear_presences_for_tests()
    clear_registries_for_tests()
    clear_output_queues_for_tests()


@pytest.mark.asyncio
async def test_ready_output_is_agent_initiated_visible() -> None:
    greeting = _agent_initiated_greeting_message(kind=DownlinkKind.USER_REPLY)
    assert ready_output_is_agent_initiated_visible(greeting)
    correlated = ReadyOutputMessage(
        message_id="out-2",
        batch_id="batch-user-1",
        kind=DownlinkKind.USER_REPLY,
        text="reply",
        sequence=2,
        message_ids=("in-1",),
    )
    assert not ready_output_is_agent_initiated_visible(correlated)


@pytest.mark.asyncio
async def test_agent_initiated_greeting_delivers_via_im_channel() -> None:
    scope = AgentScope(
        user_id="user-greet-deliver", agent_id="agent-greet-deliver"
    )
    presence = AgentChannelPresence(scope)
    api, sent = _telegram_api_with_sent_capture()
    _wire_telegram_active_channel(scope, api=api, channel_address="tg-chat-1")
    message = _agent_initiated_greeting_message(kind=DownlinkKind.USER_REPLY)

    await presence._deliver_ready_via_active_channel(message)

    assert len(sent) == 1
    assert "Hello" in sent[0] and "Inty" in sent[0]


@pytest.mark.asyncio
async def test_agent_initiated_proactive_kind_delivers_via_im_channel() -> None:
    scope = AgentScope(user_id="user-greet-pro", agent_id="agent-greet-pro")
    presence = AgentChannelPresence(scope)
    api, sent = _telegram_api_with_sent_capture()
    _wire_telegram_active_channel(scope, api=api, channel_address="tg-chat-pro")
    message = _agent_initiated_greeting_message(kind=DownlinkKind.PROACTIVE)

    await presence._deliver_ready_via_active_channel(message)

    assert len(sent) == 1
    assert "Hello" in sent[0] and "Inty" in sent[0]


@pytest.mark.asyncio
async def test_agent_initiated_greeting_unroutable_on_app_ws() -> None:
    scope = AgentScope(user_id="user-greet-ws", agent_id="agent-greet-ws")
    presence = AgentChannelPresence(scope)
    outbound = asyncio.Queue()
    _wire_app_ws_active_channel(scope, outbound=outbound)
    message = _agent_initiated_greeting_message(kind=DownlinkKind.USER_REPLY)

    with pytest.raises(OutputDeliveryUnroutableError):
        await presence._deliver_ready_via_active_channel(message)


@pytest.mark.asyncio
async def test_deliver_ready_message_acks_agent_initiated_greeting() -> None:
    scope = AgentScope(user_id="user-greet-ack", agent_id="agent-greet-ack")
    presence = AgentChannelPresence(scope)
    api, sent = _telegram_api_with_sent_capture()
    _wire_telegram_active_channel(scope, api=api, channel_address="tg-chat-2")
    message = _agent_initiated_greeting_message(kind=DownlinkKind.USER_REPLY)
    fake_queue = MagicMock()
    fake_queue.ack_delivered = AsyncMock()
    fake_queue.skip_delivery = AsyncMock()

    with patch(
        "app.services.agentic_channel.serving.get_output_queue_for_scope",
        return_value=fake_queue,
    ):
        result = await _deliver_ready_message(
            message=message,
            deliver_message=presence._deliver_ready_via_active_channel,
            scope=scope,
        )

    assert result == "Hello from Inty."
    assert len(sent) == 1
    fake_queue.ack_delivered.assert_awaited_once()
    fake_queue.skip_delivery.assert_not_awaited()


@pytest.mark.asyncio
async def test_greet_on_sign_on_end_to_end_delivers_to_telegram() -> None:
    scope = AgentScope(user_id="user-greet-e2e", agent_id="agent-greet-e2e")
    presence = AgentChannelPresence(scope)
    api, sent = _telegram_api_with_sent_capture()
    _wire_telegram_active_channel(scope, api=api, channel_address="tg-chat-e2e")
    fake_model = MagicMock()

    class _FakeRecord:
        message_id = "msg-greet-e2e"
        text = "Hello from Inty."
        sequence = 1

    with patch(
        "app.services.agentic_channel.presence.resolve_chat_model_for_scope",
        new_callable=AsyncMock,
        return_value=fake_model,
    ):
        with patch(
            "app.services.agentic_channel.presence.run_companion_implicit_sign_on_greeting_turn_for_api",
            new_callable=AsyncMock,
            return_value=CompanionTurnResult(assistant_text="Hello from Inty."),
        ):
            with patch(
                "app.core.companion_harness.agentic_companion.output_queue.AsyncSessionLocal"
            ) as session_cls:
                session = AsyncMock()
                session.__aenter__.return_value = session
                session.__aexit__.return_value = None
                session_cls.return_value = session
                repo = AsyncMock()
                repo.append_agent_output = AsyncMock(return_value=_FakeRecord())
                with patch(
                    "app.core.companion_harness.agentic_companion.output_queue.PostgresOutputQueueRepository",
                    return_value=repo,
                ):
                    await presence.greet_on_sign_on(
                        runtime_channel=GatewayKind.TELEGRAM,
                    )
                    await flush_scope_output_queue_ready(
                        scope,
                        deliver_message=presence._deliver_ready_via_active_channel,
                    )

    assert len(sent) == 1
    assert "Hello" in sent[0] and "Inty" in sent[0]


@pytest.mark.asyncio
async def test_greet_on_sign_on_silent_skips_output_queue() -> None:
    scope = AgentScope(
        user_id="user-greet-silent", agent_id="agent-greet-silent"
    )
    presence = AgentChannelPresence(scope)
    fake_model = MagicMock()
    fake_queue = MagicMock()
    fake_queue.append_visible_message = AsyncMock()

    with patch(
        "app.services.agentic_channel.presence.resolve_chat_model_for_scope",
        new_callable=AsyncMock,
        return_value=fake_model,
    ):
        with patch(
            "app.services.agentic_channel.presence.run_companion_implicit_sign_on_greeting_turn_for_api",
            new_callable=AsyncMock,
            return_value=CompanionTurnResult(
                assistant_text="",
            ),
        ):
            with patch(
                "app.services.agentic_channel.presence.get_output_queue_for_scope",
                return_value=fake_queue,
            ):
                await presence.greet_on_sign_on(
                    runtime_channel=GatewayKind.TELEGRAM,
                )

    fake_queue.append_visible_message.assert_not_awaited()
