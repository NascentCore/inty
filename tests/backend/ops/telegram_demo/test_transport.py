"""TelegramTransport routes inbound text by telegram channel_address."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from io import BytesIO
from urllib.error import HTTPError

from unittest.mock import patch

import pytest
from sqlalchemy import delete

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.db.session import AsyncSessionLocal
from app.external_services.telegram_bot_api import (
    TelegramBotApi,
    TelegramIncomingMessage,
)
from app.models.agent import Agent
from app.models.agent_channel_endpoint import AgentChannelEndpoint
from app.models.companion_bond import CompanionBond
from app.models.user import User
from app.services.agentic_channel.channel_runtime import clear_registries_for_tests
from app.services.agentic_channel.endpoints import resolve_scope
from app.services.agentic_channel.presence import clear_presences_for_tests
from app.services.agentic_channel.provision import provision_agent_for_channel_onboard
from backend.ops.telegram_demo import session_store
from backend.ops.telegram_demo.transport import TelegramTransport


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _fake_urlopen(request, timeout=15):
    url = request.full_url
    if url.endswith("/getMe"):
        return _FakeResponse(
            {
                "ok": True,
                "result": {"id": 42, "username": "demo_bot"},
            }
        )
    if "/getUpdates" in url:
        return _FakeResponse({"ok": True, "result": []})
    if url.endswith("/sendMessage"):
        return _FakeResponse({"ok": True, "result": {}})
    raise HTTPError(url, 404, "not found", hdrs=None, fp=BytesIO())


@pytest.fixture(autouse=True)
async def _reset_transport_store() -> None:
    session_store.clear_all_for_tests()
    clear_registries_for_tests()
    clear_presences_for_tests()
    yield
    session_store.clear_all_for_tests()
    clear_registries_for_tests()
    clear_presences_for_tests()


async def _cleanup_scope(scope: AgentScope) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(AgentChannelEndpoint).where(
                AgentChannelEndpoint.user_id == scope.user_id
            )
        )
        await db.execute(
            delete(CompanionBond).where(CompanionBond.user_id == scope.user_id)
        )
        await db.execute(delete(Agent).where(Agent.creator_id == scope.user_id))
        await db.execute(delete(User).where(User.id == scope.user_id))
        await db.commit()


@pytest.mark.asyncio
async def test_handle_inbound_channel_user_id_mismatch_notifies() -> None:
    tag = uuid.uuid4().hex[:10]
    telegram_chat_id = f"tg-chat-{tag}"
    channel_user_id = f"tg-user-{tag}"
    provision = await provision_agent_for_channel_onboard(
        channel=CompanionRuntimeChannel.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    sent: list[str] = []
    api = TelegramBotApi(bot_token="route-test-token", urlopen=_fake_urlopen)
    transport = TelegramTransport(api=api)

    async def capture(*, chat_id: str, text: str, scope=None) -> None:
        sent.append(text)

    transport._send_channel_text = capture  # type: ignore[method-assign]
    inbound = TelegramIncomingMessage(
        update_id=1,
        chat_id=telegram_chat_id,
        channel_user_id="wrong-user-id",
        text="你好",
        local_received_at=time.time(),
    )
    await transport._handle_inbound(inbound)
    assert any("身份" in message for message in sent)
    await _cleanup_scope(provision.scope)


@pytest.mark.asyncio
async def test_handle_inbound_unknown_start_token_prompts_onboard() -> None:
    sent: list[str] = []
    api = TelegramBotApi(bot_token="route-test-token", urlopen=_fake_urlopen)
    transport = TelegramTransport(api=api)

    async def capture(*, chat_id: str, text: str, scope=None) -> None:
        sent.append(text)

    transport._send_channel_text = capture  # type: ignore[method-assign]
    inbound = TelegramIncomingMessage(
        update_id=3,
        chat_id="999",
        channel_user_id="888",
        text="/start agent_some-id",
        local_received_at=time.time(),
    )
    await transport._handle_inbound(inbound)
    assert any("/start" in message for message in sent)


@pytest.mark.asyncio
async def test_handle_inbound_unknown_chat_prompts_onboard() -> None:
    sent: list[str] = []
    api = TelegramBotApi(bot_token="route-test-token", urlopen=_fake_urlopen)
    transport = TelegramTransport(api=api)

    async def capture(*, chat_id: str, text: str, scope=None) -> None:
        sent.append(text)

    transport._send_channel_text = capture  # type: ignore[method-assign]
    inbound = TelegramIncomingMessage(
        update_id=2,
        chat_id="999",
        channel_user_id="888",
        text="hello",
        local_received_at=time.time(),
    )
    await transport._handle_inbound(inbound)
    assert any("/start" in message for message in sent)


@pytest.mark.asyncio
async def test_concurrent_onboard_both_welcome_without_assert() -> None:
    tag = uuid.uuid4().hex[:10]
    telegram_chat_id = f"tg-race-{tag}"
    channel_user_id = f"tg-user-{tag}"
    sent: list[str] = []
    api = TelegramBotApi(bot_token="race-test-token", urlopen=_fake_urlopen)
    transport = TelegramTransport(api=api)

    async def capture(*, chat_id: str, text: str, scope=None) -> None:
        sent.append(text)

    transport._send_channel_text = capture  # type: ignore[method-assign]
    inbound = TelegramIncomingMessage(
        update_id=10,
        chat_id=telegram_chat_id,
        channel_user_id=channel_user_id,
        text="/start",
        local_received_at=time.time(),
    )
    await asyncio.gather(
        transport._handle_onboard(inbound=inbound),
        transport._handle_onboard(inbound=inbound),
    )
    assert all("欢迎" in message for message in sent)
    scope = await resolve_scope(
        channel=CompanionRuntimeChannel.TELEGRAM,
        channel_address=telegram_chat_id,
    )
    assert scope is not None
    await _cleanup_scope(scope)


@pytest.mark.asyncio
async def test_handle_inbound_sends_channel_error_from_presence() -> None:
    tag = uuid.uuid4().hex[:10]
    telegram_chat_id = f"tg-chat-{tag}"
    channel_user_id = f"tg-user-{tag}"
    provision = await provision_agent_for_channel_onboard(
        channel=CompanionRuntimeChannel.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    sent: list[str] = []
    api = TelegramBotApi(bot_token="route-test-token", urlopen=_fake_urlopen)
    transport = TelegramTransport(api=api)

    async def capture(*, chat_id: str, text: str, scope=None) -> None:
        sent.append(text)

    transport._send_channel_text = capture  # type: ignore[method-assign]

    class _ErrorPresence:
        async def handle_user_text(
            self,
            user_text: str,
            *,
            runtime_channel: CompanionRuntimeChannel,
        ) -> str:
            return "Companion 回合失败，请查看 Ops 日志。"

    with patch(
        "backend.ops.telegram_demo.transport.get_presence",
        return_value=_ErrorPresence(),
    ):
        inbound = TelegramIncomingMessage(
            update_id=20,
            chat_id=telegram_chat_id,
            channel_user_id=channel_user_id,
            text="你好",
            local_received_at=time.time(),
        )
        await transport._handle_inbound(inbound)

    assert sent == ["Companion 回合失败，请查看 Ops 日志。"]
    await _cleanup_scope(provision.scope)
