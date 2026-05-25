"""Postgres persistence for Ops WeChat demo **bridge** rows.

**Bridge** (not the QR-login phase): one live ``WeixinChannelSession`` relay after QR
success — Hermes/iLink Weixin bot on one side, long-lived Inty ``/api/v1/chat/ws`` on
the other. Inbound WeChat DMs go to the companion; proactive Inty downlink goes to
``last_peer_id``.

Each running bridge upserts one ``ops_wechat_demo_bridges`` row (credentials +
binding snapshot). Ops restart calls ``list_bridges()`` and reattaches channels without
QR. Stop/fail deletes the row. Inline Weixin creds only — no hermes_home JSON or
``load_weixin_account``.

``weixin_token`` (iLink ``bot_token`` after scan confirm): **no fixed TTL in the
protocol** — valid until iLink returns ``errcode=-14`` on long-poll/send (see
``ILINK_SESSION_EXPIRED_ERRCODE`` in ``ilink_qr_client``). Persisted rows may hold an
already-expired token after Ops restore; channel start / ``-14`` then requires re-QR.

Manual release smoke (QR + WeChat DM + Ops restart): see
``.cursor/skills/wechat-demo-bridge-restore-smoke/SKILL.md``.

TODO(wechat-demo-bridge-jwt): ``inty_jwt`` is static Bearer from Start QR UI; bind to
user-auth + refresh instead — see plan Follow-up TODO.
"""

from __future__ import annotations

from datetime import datetime

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.ops_wechat_demo_bridge import OpsWechatDemoBridge


class PersistedWechatDemoBridge(BaseModel):
    """Serializable bridge snapshot: enough to restart ``WeixinChannelSession`` without QR.

    One bridge = one demo ``session_id`` in ``BRIDGE_RUNNING`` phase (see
    ``session_store._StorePhase``). Distinct from the in-memory demo session, which also
    covers QR orchestration; this model only holds the Weixin↔Inty relay credentials.
    """

    session_id: str = Field(
        ...,
        min_length=1,
        description="Ops WeChat demo session UUID; WeixinChannelBinding.user_id.",
    )
    inty_api_base_url: str = Field(
        ...,
        min_length=1,
        description="Inty HTTP API origin used by IntyWsChannelClient to open the companion WebSocket.",
    )
    inty_jwt: str = Field(
        ...,
        min_length=1,
        description="Bearer JWT for Inty WS auth; persisted for Ops restart resume.",
    )
    agent_id: str = Field(
        ...,
        min_length=1,
        description="Inty companion agent_id routed on that WebSocket for inbound/outbound chat.",
    )
    weixin_account_id: str = Field(
        ...,
        min_length=1,
        description="iLink Weixin bot account id.",
    )
    weixin_token: str = Field(
        ...,
        min_length=1,
        description=(
            "iLink bot_token after QR confirm; no expires_in/TTL from API — usable until "
            "getupdates/sendmessage return errcode=-14 (ILINK_SESSION_EXPIRED_ERRCODE). "
            "Then re-scan QR."
        ),
    )
    weixin_base_url: str = Field(
        ...,
        min_length=1,
        description="iLink API base URL.",
    )
    last_peer_id: str | None = Field(
        default=None,
        description="Most recent inbound WeChat DM peer_id; proactive downlink targets this after restore (interim until 1:1 binding).",
    )
    last_peer_seen_at: datetime | None = Field(
        default=None,
        description="UTC time when last_peer_id last sent an inbound message; None if no peer has messaged yet.",
    )

    model_config = ConfigDict(from_attributes=True)


def record_from_binding_fields(
    session_id: str,
    inty_api_base_url: str,
    inty_jwt: str,
    agent_id: str,
    weixin_account_id: str,
    weixin_token: str,
    weixin_base_url: str,
    last_peer_id: str | None,
    last_peer_seen_at: datetime | None,
) -> PersistedWechatDemoBridge:
    return PersistedWechatDemoBridge(
        session_id=session_id,
        inty_api_base_url=inty_api_base_url,
        inty_jwt=inty_jwt,
        agent_id=agent_id,
        weixin_account_id=weixin_account_id,
        weixin_token=weixin_token,
        weixin_base_url=weixin_base_url,
        last_peer_id=last_peer_id,
        last_peer_seen_at=last_peer_seen_at,
    )


async def upsert_bridge(record: PersistedWechatDemoBridge) -> None:
    assert record.session_id != ""
    payload = record.model_dump()
    async with AsyncSessionLocal() as db:
        row = await db.get(OpsWechatDemoBridge, record.session_id)
        if row is None:
            db.add(OpsWechatDemoBridge(**payload))
        else:
            for key, value in payload.items():
                if key != "session_id":
                    setattr(row, key, value)
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception(
                "wechat_demo bridge persist failed session_id={}",
                record.session_id,
            )
            raise


async def delete_bridge(session_id: str) -> None:
    assert session_id != ""
    async with AsyncSessionLocal() as db:
        row = await db.get(OpsWechatDemoBridge, session_id)
        if row is not None:
            await db.delete(row)
            await db.commit()


async def list_bridges() -> list[PersistedWechatDemoBridge]:
    """All persisted bridges (``ops_wechat_demo_bridges`` rows) for Ops restart restore."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(OpsWechatDemoBridge).order_by(OpsWechatDemoBridge.session_id)
        )
        rows = result.scalars().all()
        return [PersistedWechatDemoBridge.model_validate(row) for row in rows]
