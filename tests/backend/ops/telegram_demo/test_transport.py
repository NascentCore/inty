"""TelegramTransport routes inbound text by telegram channel_address."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import UTC, datetime
from io import BytesIO
from urllib.error import HTTPError
from urllib.parse import parse_qs

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import delete, select

from app.core.companion_harness.agent_channel.gateway import GatewayKind
from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agent_channel.gateway import (
    GatewayKind,
)
from app.db.session import AsyncSessionLocal
from app.external_services.telegram_bot_api import (
    TelegramBotApi,
    TelegramIncomingMessage,
)
from app.models.agent import Agent
from app.models.agent_channel_endpoint import AgentChannelEndpoint
from app.models.companion_bond import CompanionBond, CompanionBondState
from app.models.user import User
from app.services.agentic_channel.channel_runtime import (
    clear_registries_for_tests,
)
from app.services.agentic_channel.endpoints import resolve_scope
from app.core.companion_harness.companion.models import CompanionTurnResult
from app.services.agentic_channel.presence import (
    clear_presences_for_tests,
    get_presence,
)
from app.services.agentic_channel.serving import flush_scope_output_queue_ready
from app.services.agentic_channel.companion_bonds import (
    deactivate_companion_bond,
    get_companion_bond_for_scope,
    pause_companion_bond_runtime,
)
from app.services.agentic_channel.companion_guest_provision import (
    add_companion_guest_agent_for_user,
)
from app.services.agentic_channel.provision import (
    ChannelProvisionResult,
    provision_agent_for_channel_onboard,
)
from backend.ops.telegram_demo import session_store
from backend.ops.telegram_demo.transport import (
    TelegramTransport,
    _BOND_UNAVAILABLE,
    _IDENTITY_MISMATCH,
    _ONBOARD_HINT,
    _ONBOARD_NOTICE_NEW,
    _ONBOARD_NOTICE_RETURNING,
    _format_transport_notice,
)


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


def test_transport_onboard_copy_is_english() -> None:
    messages = (
        _ONBOARD_NOTICE_NEW,
        _ONBOARD_NOTICE_RETURNING,
        _ONBOARD_HINT,
        _IDENTITY_MISMATCH,
        _BOND_UNAVAILABLE,
    )

    assert "/telegram" in _ONBOARD_HINT
    assert "/start" in _ONBOARD_HINT
    assert "Ops" not in _ONBOARD_HINT
    assert "waking up" in _ONBOARD_NOTICE_NEW
    assert all(
        not any("\u4e00" <= char <= "\u9fff" for char in message)
        for message in messages
    )


def test_format_transport_notice_wraps_body_in_italic_html() -> None:
    assert _format_transport_notice("hello") == "<i>hello</i>"


@pytest.mark.asyncio
async def test_send_channel_text_uses_html_parse_mode() -> None:
    captured: list[bytes] = []

    def capturing_urlopen(request, timeout=15):
        if request.full_url.endswith("/sendMessage"):
            captured.append(request.data)
            return _FakeResponse({"ok": True, "result": {}})
        return _fake_urlopen(request, timeout)

    api = TelegramBotApi(bot_token="notice-token", urlopen=capturing_urlopen)
    transport = TelegramTransport(api=api)
    await transport._send_channel_text(
        chat_id="5078060274",
        text=_ONBOARD_NOTICE_NEW,
    )
    assert len(captured) == 1
    fields = parse_qs(captured[0].decode("utf-8"))
    assert fields["parse_mode"] == ["HTML"]
    assert fields["text"] == [_format_transport_notice(_ONBOARD_NOTICE_NEW)]


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


async def _run_onboard_start(
    *,
    telegram_chat_id: str,
    channel_user_id: str,
) -> tuple[list[str], MagicMock]:
    sent: list[str] = []
    api = TelegramBotApi(bot_token="onboard-test", urlopen=_fake_urlopen)
    transport = TelegramTransport(api=api)

    async def capture(*, chat_id: str, text: str, scope=None) -> None:
        sent.append(text)

    transport._send_channel_text = capture  # type: ignore[method-assign]
    mock_presence = MagicMock()
    mock_presence.greet_on_sign_on = AsyncMock()

    with patch(
        "backend.ops.telegram_demo.transport.get_presence",
        return_value=mock_presence,
    ):
        inbound = TelegramIncomingMessage(
            update_id=60,
            chat_id=telegram_chat_id,
            channel_user_id=channel_user_id,
            text="/start onboard",
            local_received_at=time.time(),
        )
        await transport._handle_onboard(inbound=inbound)
    return sent, mock_presence


async def _assert_onboard_rejects_bad_bond(
    *,
    telegram_chat_id: str,
    channel_user_id: str,
    scope: AgentScope,
) -> None:
    sent, mock_presence = await _run_onboard_start(
        telegram_chat_id=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    assert sent == [_BOND_UNAVAILABLE]
    assert _ONBOARD_NOTICE_RETURNING not in sent
    assert get_presence(scope) is None
    mock_presence.greet_on_sign_on.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_inbound_channel_user_id_mismatch_notifies() -> None:
    tag = uuid.uuid4().hex[:10]
    telegram_chat_id = f"tg-chat-{tag}"
    channel_user_id = f"tg-user-{tag}"
    provision = await provision_agent_for_channel_onboard(
        channel=GatewayKind.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    sent: list[str] = []
    api = TelegramBotApi(bot_token="route-test-token", urlopen=_fake_urlopen)
    transport = TelegramTransport(api=api)

    async def capture(*, chat_id: str, text: str) -> None:
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
    assert any("match" in message.lower() for message in sent)
    await _cleanup_scope(provision.scope)


@pytest.mark.asyncio
async def test_handle_inbound_unknown_start_token_prompts_onboard() -> None:
    sent: list[str] = []
    api = TelegramBotApi(bot_token="route-test-token", urlopen=_fake_urlopen)
    transport = TelegramTransport(api=api)

    async def capture(*, chat_id: str, text: str) -> None:
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

    async def capture(*, chat_id: str, text: str) -> None:
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

    async def capture(*, chat_id: str, text: str) -> None:
        sent.append(text)

    transport._send_channel_text = capture  # type: ignore[method-assign]
    mock_presence = MagicMock()
    mock_presence.greet_on_sign_on = AsyncMock()

    with patch(
        "backend.ops.telegram_demo.transport.get_presence",
        return_value=mock_presence,
    ):
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
    assert mock_presence.greet_on_sign_on.await_count >= 1
    scope = await resolve_scope(
        channel=GatewayKind.TELEGRAM,
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
        channel=GatewayKind.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    sent: list[str] = []
    api = TelegramBotApi(bot_token="route-test-token", urlopen=_fake_urlopen)
    transport = TelegramTransport(api=api)

    async def capture(*, chat_id: str, text: str) -> None:
        sent.append(text)

    transport._send_channel_text = capture  # type: ignore[method-assign]

    class _ErrorPresence:
        async def handle_user_text(
            self,
            user_text: str,
            *,
            runtime_channel: GatewayKind,
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


@pytest.mark.asyncio
async def test_handle_inbound_resumes_paused_companion_runtime() -> None:
    tag = uuid.uuid4().hex[:10]
    telegram_chat_id = f"tg-paused-{tag}"
    channel_user_id = f"tg-user-{tag}"
    provision = await provision_agent_for_channel_onboard(
        channel=GatewayKind.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    async with AsyncSessionLocal() as db:
        await pause_companion_bond_runtime(db, provision.scope)
        await db.commit()

    class _CapturePresence:
        def __init__(self) -> None:
            self.texts: list[str] = []

        async def handle_user_text(
            self,
            user_text: str,
            *,
            runtime_channel: GatewayKind,
        ) -> str:
            self.texts.append(user_text)
            return ""

    presence = _CapturePresence()
    api = TelegramBotApi(bot_token="route-test-token", urlopen=_fake_urlopen)
    transport = TelegramTransport(api=api)
    with patch(
        "backend.ops.telegram_demo.transport.get_presence",
        return_value=presence,
    ):
        inbound = TelegramIncomingMessage(
            update_id=21,
            chat_id=telegram_chat_id,
            channel_user_id=channel_user_id,
            text="I am back",
            local_received_at=time.time(),
        )
        await transport._handle_inbound(inbound)

    assert presence.texts == ["I am back"]
    async with AsyncSessionLocal() as db:
        bond = await get_companion_bond_for_scope(db, provision.scope)
        assert bond is not None
        assert bond.runtime_paused_at is None
        assert bond.last_resumed_at is not None
    await _cleanup_scope(provision.scope)


@pytest.mark.asyncio
async def test_onboard_new_user_triggers_greeting() -> None:
    tag = uuid.uuid4().hex[:10]
    telegram_chat_id = f"tg-greet-{tag}"
    channel_user_id = f"tg-user-{tag}"
    sent: list[str] = []
    api = TelegramBotApi(bot_token="greet-test-token", urlopen=_fake_urlopen)
    transport = TelegramTransport(api=api)

    async def capture(*, chat_id: str, text: str) -> None:
        sent.append(text)

    transport._send_channel_text = capture  # type: ignore[method-assign]
    mock_presence = MagicMock()
    mock_presence.greet_on_sign_on = AsyncMock()

    with patch(
        "backend.ops.telegram_demo.transport.get_presence",
        return_value=mock_presence,
    ):
        inbound = TelegramIncomingMessage(
            update_id=50,
            chat_id=telegram_chat_id,
            channel_user_id=channel_user_id,
            text="/start onboard",
            local_received_at=time.time(),
        )
        await transport._handle_onboard(inbound=inbound)

    assert sent == [_ONBOARD_NOTICE_NEW]
    mock_presence.greet_on_sign_on.assert_awaited_once()
    scope = await resolve_scope(
        channel=GatewayKind.TELEGRAM,
        channel_address=telegram_chat_id,
    )
    assert scope is not None
    await _cleanup_scope(scope)


@pytest.mark.asyncio
async def test_onboard_new_user_delivers_greeting_message() -> None:
    tag = uuid.uuid4().hex[:10]
    telegram_chat_id = f"tg-deliver-{tag}"
    channel_user_id = f"tg-user-{tag}"
    sent_bodies: list[str] = []

    def capturing_urlopen(request, timeout=15):
        if request.full_url.endswith("/sendMessage"):
            sent_bodies.append(request.data.decode("utf-8"))
            return _FakeResponse({"ok": True, "result": {}})
        return _fake_urlopen(request, timeout)

    api = TelegramBotApi(
        bot_token="deliver-greet-token",
        urlopen=capturing_urlopen,
    )
    transport = TelegramTransport(api=api)
    fake_model = MagicMock()

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
            inbound = TelegramIncomingMessage(
                update_id=52,
                chat_id=telegram_chat_id,
                channel_user_id=channel_user_id,
                text="/start onboard",
                local_received_at=time.time(),
            )
            await transport._handle_onboard(inbound=inbound)

    scope = await resolve_scope(
        channel=GatewayKind.TELEGRAM,
        channel_address=telegram_chat_id,
    )
    assert scope is not None
    presence = get_presence(scope)
    assert presence is not None
    await flush_scope_output_queue_ready(
        scope,
        deliver_message=presence._deliver_ready_via_active_channel,
    )

    assert len(sent_bodies) == 2
    notice_fields = parse_qs(sent_bodies[0])
    greeting_fields = parse_qs(sent_bodies[1])
    assert notice_fields["parse_mode"] == ["HTML"]
    assert notice_fields["text"] == [
        _format_transport_notice(_ONBOARD_NOTICE_NEW)
    ]
    assert "parse_mode" not in greeting_fields
    assert "Hello" in greeting_fields["text"][0]
    assert "Inty" in greeting_fields["text"][0]
    await _cleanup_scope(scope)


@pytest.mark.asyncio
async def test_onboard_returning_rejects_deleted_bond() -> None:
    tag = uuid.uuid4().hex[:10]
    telegram_chat_id = f"tg-bond-del-{tag}"
    channel_user_id = f"tg-user-{tag}"
    provision = await provision_agent_for_channel_onboard(
        channel=GatewayKind.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(CompanionBond).where(
                CompanionBond.user_id == provision.scope.user_id
            )
        )
        await db.commit()

    await _assert_onboard_rejects_bad_bond(
        telegram_chat_id=telegram_chat_id,
        channel_user_id=channel_user_id,
        scope=provision.scope,
    )
    await _cleanup_scope(provision.scope)


@pytest.mark.asyncio
async def test_onboard_returning_rejects_inactive_bond() -> None:
    tag = uuid.uuid4().hex[:10]
    telegram_chat_id = f"tg-bond-inact-{tag}"
    channel_user_id = f"tg-user-{tag}"
    provision = await provision_agent_for_channel_onboard(
        channel=GatewayKind.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    async with AsyncSessionLocal() as db:
        await deactivate_companion_bond(db, provision.scope)
        await db.commit()

    await _assert_onboard_rejects_bad_bond(
        telegram_chat_id=telegram_chat_id,
        channel_user_id=channel_user_id,
        scope=provision.scope,
    )
    await _cleanup_scope(provision.scope)


@pytest.mark.asyncio
async def test_onboard_returning_rejects_deleted_user() -> None:
    tag = uuid.uuid4().hex[:10]
    telegram_chat_id = f"tg-bond-user-{tag}"
    channel_user_id = f"tg-user-{tag}"
    provision = await provision_agent_for_channel_onboard(
        channel=GatewayKind.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    async with AsyncSessionLocal() as db:
        user_row = await db.execute(
            select(User).where(User.id == provision.scope.user_id)
        )
        user = user_row.scalar_one()
        user.deleted_at = datetime.now(UTC)
        await db.commit()

    await _assert_onboard_rejects_bad_bond(
        telegram_chat_id=telegram_chat_id,
        channel_user_id=channel_user_id,
        scope=provision.scope,
    )
    await _cleanup_scope(provision.scope)


@pytest.mark.asyncio
async def test_onboard_returning_rejects_deleted_agent() -> None:
    tag = uuid.uuid4().hex[:10]
    telegram_chat_id = f"tg-bond-agent-{tag}"
    channel_user_id = f"tg-user-{tag}"
    provision = await provision_agent_for_channel_onboard(
        channel=GatewayKind.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    async with AsyncSessionLocal() as db:
        agent_row = await db.execute(
            select(Agent).where(Agent.id == provision.scope.agent_id)
        )
        agent = agent_row.scalar_one()
        agent.deleted_at = datetime.now(UTC)
        await db.commit()

    await _assert_onboard_rejects_bad_bond(
        telegram_chat_id=telegram_chat_id,
        channel_user_id=channel_user_id,
        scope=provision.scope,
    )
    await _cleanup_scope(provision.scope)


@pytest.mark.asyncio
async def test_onboard_returning_rejects_ambiguous_bond() -> None:
    tag = uuid.uuid4().hex[:10]
    telegram_chat_id = f"tg-bond-ambig-{tag}"
    channel_user_id = f"tg-user-{tag}"
    provision = await provision_agent_for_channel_onboard(
        channel=GatewayKind.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    async with AsyncSessionLocal() as db:
        second_agent = await add_companion_guest_agent_for_user(
            db,
            user_id=provision.scope.user_id,
            gateway=GatewayKind.TELEGRAM,
        )
        db.add(
            CompanionBond(
                id=str(uuid.uuid4()),
                user_id=provision.scope.user_id,
                agent_id=second_agent.id,
                state=CompanionBondState.ACTIVE,
            )
        )
        await db.commit()

    await _assert_onboard_rejects_bad_bond(
        telegram_chat_id=telegram_chat_id,
        channel_user_id=channel_user_id,
        scope=provision.scope,
    )
    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(CompanionBond).where(
                CompanionBond.user_id == provision.scope.user_id,
                CompanionBond.agent_id != provision.scope.agent_id,
            )
        )
        await db.commit()
    await _cleanup_scope(provision.scope)


@pytest.mark.asyncio
async def test_onboard_returning_welcomes_paused_bond() -> None:
    tag = uuid.uuid4().hex[:10]
    telegram_chat_id = f"tg-bond-pause-{tag}"
    channel_user_id = f"tg-user-{tag}"
    provision = await provision_agent_for_channel_onboard(
        channel=GatewayKind.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    async with AsyncSessionLocal() as db:
        await pause_companion_bond_runtime(db, provision.scope)
        await db.commit()

    sent: list[str] = []
    api = TelegramBotApi(bot_token="pause-onboard-token", urlopen=_fake_urlopen)
    transport = TelegramTransport(api=api)

    async def capture(*, chat_id: str, text: str, scope=None) -> None:
        sent.append(text)

    transport._send_channel_text = capture  # type: ignore[method-assign]
    inbound = TelegramIncomingMessage(
        update_id=62,
        chat_id=telegram_chat_id,
        channel_user_id=channel_user_id,
        text="/start onboard",
        local_received_at=time.time(),
    )
    await transport._handle_onboard(inbound=inbound)

    assert sent == [_ONBOARD_NOTICE_RETURNING]
    assert get_presence(provision.scope) is not None
    async with AsyncSessionLocal() as db:
        bond = await get_companion_bond_for_scope(db, provision.scope)
        assert bond is not None
        assert bond.runtime_paused_at is None
    await _cleanup_scope(provision.scope)


@pytest.mark.asyncio
async def test_onboard_new_user_gate_before_greeting() -> None:
    tag = uuid.uuid4().hex[:10]
    telegram_chat_id = f"tg-bond-new-{tag}"
    channel_user_id = f"tg-user-{tag}"
    provision = await provision_agent_for_channel_onboard(
        channel=GatewayKind.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    async with AsyncSessionLocal() as db:
        await deactivate_companion_bond(db, provision.scope)
        await db.commit()

    sent: list[str] = []
    api = TelegramBotApi(bot_token="new-gate-token", urlopen=_fake_urlopen)
    transport = TelegramTransport(api=api)

    async def capture(*, chat_id: str, text: str, scope=None) -> None:
        sent.append(text)

    transport._send_channel_text = capture  # type: ignore[method-assign]
    mock_presence = MagicMock()
    mock_presence.greet_on_sign_on = AsyncMock()

    with patch(
        "backend.ops.telegram_demo.transport.get_presence",
        return_value=mock_presence,
    ):
        inbound = TelegramIncomingMessage(
            update_id=61,
            chat_id=telegram_chat_id,
            channel_user_id=channel_user_id,
            text="/start onboard",
            local_received_at=time.time(),
        )
        await transport._activate_provision(
            inbound=inbound,
            provision=ChannelProvisionResult(
                scope=provision.scope,
                is_new_user=True,
                channel_address=telegram_chat_id,
                channel_user_id=channel_user_id,
            ),
        )

    assert sent == [_BOND_UNAVAILABLE]
    assert get_presence(provision.scope) is None
    mock_presence.greet_on_sign_on.assert_not_awaited()
    await _cleanup_scope(provision.scope)


@pytest.mark.asyncio
async def test_onboard_greeting_failure_falls_back() -> None:
    tag = uuid.uuid4().hex[:10]
    telegram_chat_id = f"tg-greet-fail-{tag}"
    channel_user_id = f"tg-user-{tag}"
    sent: list[str] = []
    api = TelegramBotApi(bot_token="greet-fail-token", urlopen=_fake_urlopen)
    transport = TelegramTransport(api=api)

    async def capture(*, chat_id: str, text: str) -> None:
        sent.append(text)

    transport._send_channel_text = capture  # type: ignore[method-assign]
    mock_presence = MagicMock()
    mock_presence.greet_on_sign_on = AsyncMock(
        side_effect=RuntimeError("greeting failed")
    )

    with patch(
        "backend.ops.telegram_demo.transport.get_presence",
        return_value=mock_presence,
    ):
        inbound = TelegramIncomingMessage(
            update_id=51,
            chat_id=telegram_chat_id,
            channel_user_id=channel_user_id,
            text="/start onboard",
            local_received_at=time.time(),
        )
        await transport._handle_onboard(inbound=inbound)

    assert sent == [_ONBOARD_NOTICE_NEW]
    scope = await resolve_scope(
        channel=GatewayKind.TELEGRAM,
        channel_address=telegram_chat_id,
    )
    assert scope is not None
    await _cleanup_scope(scope)
