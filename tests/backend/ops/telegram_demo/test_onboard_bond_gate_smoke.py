"""End-to-end smoke for Telegram onboard ACTIVE bond gate (#3533).

Manual release smoke (real Telegram + Ops): ``.cursor/skills/telegram-demo-restore-smoke/SKILL.md``.
"""

from __future__ import annotations

import json
import time
import uuid
from io import BytesIO
from urllib.error import HTTPError

import pytest
from loguru import logger
from sqlalchemy import delete

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agent_channel.channel_kind import (
    ChannelKind,
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
from app.services.agentic_channel.channel_runtime import (
    clear_registries_for_tests,
)
from app.services.agentic_channel.companion_bonds import (
    deactivate_companion_bond,
    get_companion_bond_for_scope,
    pause_companion_bond_runtime,
)
from app.services.agentic_channel.presence import (
    clear_presences_for_tests,
    get_presence,
)
from app.services.agentic_channel.provision import (
    provision_agent_for_channel_onboard,
)
from backend.ops.telegram_demo import session_store
from backend.ops.telegram_demo.transport import (
    TelegramTransport,
    _BOND_UNAVAILABLE,
    _ONBOARD_NOTICE_RETURNING,
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
            {"ok": True, "result": {"id": 42, "username": "demo_bot"}}
        )
    if "/getUpdates" in url:
        return _FakeResponse({"ok": True, "result": []})
    if url.endswith("/sendMessage"):
        return _FakeResponse({"ok": True, "result": {}})
    raise HTTPError(url, 404, "not found", hdrs=None, fp=BytesIO())


@pytest.fixture
def log_capture():
    """Capture loguru WARNING+ lines for structured-log smoke assertions."""
    records: list[str] = []

    def _sink(message) -> None:
        records.append(message.record["message"])

    handler_id = logger.add(_sink, level="WARNING")
    yield records
    logger.remove(handler_id)


@pytest.fixture(autouse=True)
async def _reset_telegram_demo_state() -> None:
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


async def _send_onboard(
    transport: TelegramTransport,
    *,
    telegram_chat_id: str,
    channel_user_id: str,
) -> list[str]:
    sent: list[str] = []

    async def capture(*, chat_id: str, text: str, scope=None) -> None:
        sent.append(text)

    transport._send_channel_text = capture  # type: ignore[method-assign]
    inbound = TelegramIncomingMessage(
        update_id=90,
        chat_id=telegram_chat_id,
        channel_user_id=channel_user_id,
        text="/start onboard",
        local_received_at=time.time(),
    )
    await transport._handle_onboard(inbound=inbound)
    return sent


@pytest.mark.asyncio
async def test_smoke_onboard_bond_gate_happy_returning_path() -> None:
    """Provisioned user with ACTIVE bond gets welcome and presence on /start onboard."""
    tag = uuid.uuid4().hex[:10]
    telegram_chat_id = f"tg-smoke-ok-{tag}"
    channel_user_id = f"tg-user-{tag}"
    provision = await provision_agent_for_channel_onboard(
        channel=ChannelKind.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    api = TelegramBotApi(bot_token="smoke-ok-token", urlopen=_fake_urlopen)
    transport = TelegramTransport(api=api)

    sent = await _send_onboard(
        transport,
        telegram_chat_id=telegram_chat_id,
        channel_user_id=channel_user_id,
    )

    assert sent == [_ONBOARD_NOTICE_RETURNING]
    assert get_presence(provision.scope) is not None
    await _cleanup_scope(provision.scope)


@pytest.mark.asyncio
async def test_smoke_onboard_bond_gate_rejects_inactive_then_restore_skips(
    log_capture: list[str],
) -> None:
    """Inactive bond: onboard rejects with static copy; Ops restore does not restart."""
    tag = uuid.uuid4().hex[:10]
    telegram_chat_id = f"tg-smoke-bad-{tag}"
    channel_user_id = f"tg-user-{tag}"
    provision = await provision_agent_for_channel_onboard(
        channel=ChannelKind.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    async with AsyncSessionLocal() as db:
        await deactivate_companion_bond(db, provision.scope)
        await db.commit()

    api = TelegramBotApi(bot_token="smoke-bad-token", urlopen=_fake_urlopen)
    transport = TelegramTransport(api=api)
    sent = await _send_onboard(
        transport,
        telegram_chat_id=telegram_chat_id,
        channel_user_id=channel_user_id,
    )

    assert sent == [_BOND_UNAVAILABLE]
    assert _ONBOARD_NOTICE_RETURNING not in sent
    assert get_presence(provision.scope) is None
    assert any(
        "telegram_onboard_rejected_bond" in line
        and provision.scope.registry_key() in line
        for line in log_capture
    )

    session_store.clear_all_for_tests()
    restore_api = TelegramBotApi(bot_token="smoke-restore-skip")
    await session_store.restore_persisted_bindings(api=restore_api)
    assert (
        session_store.get_scope_for_telegram_address(telegram_chat_id) is None
    )
    assert get_presence(provision.scope) is None

    await _cleanup_scope(provision.scope)


@pytest.mark.asyncio
async def test_smoke_onboard_bond_gate_paused_returning_welcome() -> None:
    """ACTIVE bond with runtime_paused_at: onboard welcome clears pause and starts presence."""
    tag = uuid.uuid4().hex[:10]
    telegram_chat_id = f"tg-smoke-pause-{tag}"
    channel_user_id = f"tg-user-{tag}"
    provision = await provision_agent_for_channel_onboard(
        channel=ChannelKind.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    async with AsyncSessionLocal() as db:
        await pause_companion_bond_runtime(db, provision.scope)
        await db.commit()

    api = TelegramBotApi(bot_token="smoke-pause-token", urlopen=_fake_urlopen)
    transport = TelegramTransport(api=api)
    sent = await _send_onboard(
        transport,
        telegram_chat_id=telegram_chat_id,
        channel_user_id=channel_user_id,
    )

    assert sent == [_ONBOARD_NOTICE_RETURNING]
    assert get_presence(provision.scope) is not None
    async with AsyncSessionLocal() as db:
        bond = await get_companion_bond_for_scope(db, provision.scope)
        assert bond is not None
        assert bond.runtime_paused_at is None

    await _cleanup_scope(provision.scope)
