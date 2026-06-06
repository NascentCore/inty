"""CI tests for Weixin bridge restore (mock Weixin; no QR / Hermes).

Full QR + WeChat DM flow: manual release smoke in
``.cursor/skills/weixin-bridge-restore-smoke/SKILL.md``.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import sessionmaker

from app.core.config import global_config_loaded_from_config_yaml
from app.db.session import async_engine
from app.models.agent import Agent, AgentStatus
from app.models.ops_weixin_bridge import OpsWeixinBridge
from app.models.registry import load_model_modules
from app.models.user import AuthType, Gender, User
from backend.ops.schemas.weixin_session import WeixinSessionPhase
from backend.ops.weixin_session import session_store
from backend.ops.weixin_session.session_persistence import (
    list_bridges,
    record_from_binding_fields,
    upsert_bridge,
    delete_bridge,
)


class _FakeWeixinChannelSession:
    """Stand-in for ``WeixinChannelSession`` (no Hermes / Inty WS)."""

    instances: list[_FakeWeixinChannelSession] = []
    start_raises: bool = False

    def __init__(
        self,
        binding: object,
        on_binding_peer_updated: object,
        on_ilink_session_expired: object,
    ) -> None:
        self.binding = binding
        self._on_binding_peer_updated = on_binding_peer_updated
        self._on_ilink_session_expired = on_ilink_session_expired
        self._stop = asyncio.Event()
        _FakeWeixinChannelSession.instances.append(self)

    async def start(self) -> None:
        if _FakeWeixinChannelSession.start_raises:
            raise ConnectionError("fake weixin channel start failed")

    async def run_until_stopped(self) -> None:
        await self._stop.wait()

    async def stop(self) -> None:
        self._stop.set()


@pytest.fixture
def sync_db_session():
    load_model_modules()
    from sqlalchemy import create_engine

    engine = create_engine(global_config_loaded_from_config_yaml.database.url)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture(autouse=True)
def clean_bridge_rows(sync_db_session):
    sync_db_session.execute(delete(OpsWeixinBridge))
    sync_db_session.commit()
    yield
    sync_db_session.execute(delete(OpsWeixinBridge))
    sync_db_session.commit()


@pytest.fixture
def agent_id(sync_db_session):
    user_id = f"user-weixin-{uuid.uuid4().hex[:8]}"
    aid = f"agent-weixin-{uuid.uuid4().hex[:8]}"
    sync_db_session.add(
        User(
            id=user_id,
            auth_type=AuthType.GUEST,
            device_id=f"device-{uuid.uuid4().hex[:12]}",
        )
    )
    sync_db_session.flush()
    sync_db_session.add(
        Agent(
            id=aid,
            name="Weixin Restore Test Agent",
            gender=Gender.FEMALE,
            status=AgentStatus.APPROVED,
            creator_id=user_id,
        )
    )
    sync_db_session.commit()
    yield aid
    sync_db_session.execute(
        delete(OpsWeixinBridge).where(OpsWeixinBridge.agent_id == aid)
    )
    sync_db_session.execute(delete(Agent).where(Agent.id == aid))
    sync_db_session.execute(delete(User).where(User.id == user_id))
    sync_db_session.commit()


@pytest.fixture(autouse=True)
async def reset_weixin_session_store():
    _FakeWeixinChannelSession.instances = []
    _FakeWeixinChannelSession.start_raises = False
    session_store._sessions.clear()
    session_store.WeixinChannelSession = _FakeWeixinChannelSession
    yield
    for session_id in list(session_store._sessions.keys()):
        await session_store.stop_session(session_id)
    session_store._sessions.clear()
    _FakeWeixinChannelSession.instances = []


def _bridge_record(session_id: str, agent_id: str) -> object:
    return record_from_binding_fields(
        session_id=session_id,
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="jwt-restore-test",
        agent_id=agent_id,
        weixin_account_id="wx-restore-acct",
        weixin_token="tok-restore",
        weixin_base_url="https://ilink.example",
        last_peer_id="peer-before-restore",
        last_peer_seen_at=datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc),
    )


async def _wait_bridge_running(session_id: str) -> None:
    deadline = asyncio.get_running_loop().time() + 5.0
    while asyncio.get_running_loop().time() < deadline:
        view = await session_store.get_session(session_id)
        if view is not None and view.phase == WeixinSessionPhase.BRIDGE_RUNNING:
            return
        await asyncio.sleep(0.05)
    raise AssertionError(f"session {session_id} did not reach bridge_running")


@pytest.mark.asyncio
async def test_restore_scenarios(agent_id: str) -> None:
    """Single async test: global ``AsyncSessionLocal`` breaks a second async DB test."""
    # Prior tests may close per-function event loops while global async_engine pool
    # still holds asyncpg connections bound to those loops.
    await async_engine.dispose()
    session_id = f"sess-restore-{uuid.uuid4().hex[:8]}"
    await upsert_bridge(_bridge_record(session_id, agent_id))
    assert session_store.WeixinChannelSession is _FakeWeixinChannelSession
    await session_store.restore_persisted_sessions()
    await _wait_bridge_running(session_id)

    view = await session_store.get_session(session_id)
    assert view is not None
    assert view.bridge_running is True
    rows = await list_bridges()
    assert len(rows) == 1
    assert rows[0].session_id == session_id

    stopped = await session_store.stop_session(session_id)
    assert stopped is not None
    assert stopped.phase == WeixinSessionPhase.STOPPED
    assert await list_bridges() == []

    fail_session_id = f"sess-fail-{uuid.uuid4().hex[:8]}"
    _FakeWeixinChannelSession.instances = []
    _FakeWeixinChannelSession.start_raises = True
    await upsert_bridge(_bridge_record(fail_session_id, agent_id))

    await session_store.restore_persisted_sessions()
    await asyncio.sleep(0.2)

    assert await session_store.get_session(fail_session_id) is None
    assert await list_bridges() == []
    _FakeWeixinChannelSession.start_raises = False

    peer_session_id = f"sess-peer-{uuid.uuid4().hex[:8]}"
    _FakeWeixinChannelSession.instances = []
    await upsert_bridge(_bridge_record(peer_session_id, agent_id))

    await session_store.restore_persisted_sessions()
    await _wait_bridge_running(peer_session_id)

    assert len(_FakeWeixinChannelSession.instances) == 1
    channel = _FakeWeixinChannelSession.instances[0]
    peer_updated = channel._on_binding_peer_updated
    assert peer_updated is not None
    channel.binding.last_peer_id = "peer-after-inbound"
    channel.binding.last_peer_seen_at = datetime(
        2026, 5, 25, 15, 30, tzinfo=timezone.utc
    )
    await peer_updated(channel.binding)

    rows = await list_bridges()
    assert len(rows) == 1
    assert rows[0].last_peer_id == "peer-after-inbound"
    assert rows[0].last_peer_seen_at == datetime(
        2026, 5, 25, 15, 30, tzinfo=timezone.utc
    )

    await session_store.stop_session(peer_session_id)

    roundtrip_id = f"sess-a-{uuid.uuid4().hex[:8]}"
    record = _bridge_record(roundtrip_id, agent_id)
    await upsert_bridge(record)
    listed = await list_bridges()
    assert listed == [record]
    updated = record.model_copy(
        update={
            "last_peer_id": "peer-new",
            "last_peer_seen_at": datetime(2026, 5, 25, 13, 0, tzinfo=timezone.utc),
        }
    )
    await upsert_bridge(updated)
    listed = await list_bridges()
    assert listed == [updated]
    await delete_bridge(record.session_id)
    assert await list_bridges() == []
