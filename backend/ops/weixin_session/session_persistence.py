"""Postgres persistence for Ops Weixin **bridge** rows.

**Bridge** (not the QR-login phase): one live ``WeixinChannelSession`` relay after QR
success — Hermes/iLink Weixin bot on one side, in-process companion on the other.
Inbound WeChat DMs go to the companion; proactive Inty downlink goes to
``last_peer_id``. iLink cannot detect WeChat user presence; ``last_peer_seen_at`` is
last inbound DM only (see ``backend.ops.weixin_channel``).

Each running bridge upserts one ``ops_wechat_demo_bridges`` row (credentials +
binding snapshot). Ops restart calls ``list_bridges()`` and reattaches channels without
QR. Stop/fail deletes the row. Inline Weixin creds only — no hermes_home JSON.

``weixin_token`` (iLink ``bot_token`` after scan confirm): **no fixed TTL in the
protocol** — valid until iLink returns ``errcode=-14`` on long-poll/send (see
``ILINK_SESSION_EXPIRED_ERRCODE`` in ``ilink_qr_client``). Persisted rows may hold an
already-expired token after Ops restore; channel start / ``-14`` then requires re-QR.

TODO(weixin-ilink-session-expired-user-notify): same as
``backend.ops.weixin_channel.transport`` — after ``-14``, notify QR operator via Ops
session ``error`` / ``FAILED``, not via WeChat bot DM.

Manual release smoke (QR + WeChat DM + Ops restart): see
``.cursor/skills/weixin-bridge-restore-smoke/SKILL.md``.

TODO(weixin-bridge-jwt): ``inty_jwt`` is static Bearer from onboard provision; bind to
user-auth + refresh instead — see plan Follow-up TODO.
"""

from __future__ import annotations

from datetime import datetime

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.ops_weixin_bridge import OpsWeixinBridge


class PersistedWeixinBridge(BaseModel):
    """Serializable bridge snapshot: enough to restart ``WeixinChannelSession`` without QR.

    One bridge = one session in ``BRIDGE_RUNNING`` phase (see
    ``session_store._StorePhase``). Distinct from the in-memory session, which also
    covers QR orchestration; this model only holds the Weixin↔Inty relay credentials.
    """

    session_id: str = Field(
        ...,
        min_length=1,
        description="Ops Weixin session UUID; WeixinChannelBinding.user_id.",
    )
    inty_api_base_url: str = Field(
        ...,
        min_length=1,
        description="Inty HTTP API origin for the bridge JWT and agent binding.",
    )
    inty_jwt: str = Field(
        ...,
        min_length=1,
        description="Bearer JWT for Inty companion auth; persisted for Ops restart resume.",
    )
    agent_id: str = Field(
        ...,
        min_length=1,
        description="Inty companion agent_id for inbound/outbound chat.",
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
) -> PersistedWeixinBridge:
    return PersistedWeixinBridge(
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


async def upsert_bridge(record: PersistedWeixinBridge) -> None:
    assert record.session_id != ""
    payload = record.model_dump()
    async with AsyncSessionLocal() as db:
        row = await db.get(OpsWeixinBridge, record.session_id)
        if row is None:
            db.add(OpsWeixinBridge(**payload))
        else:
            for key, value in payload.items():
                if key != "session_id":
                    setattr(row, key, value)
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception(
                "weixin bridge persist failed session_id={}",
                record.session_id,
            )
            raise


async def delete_bridge(session_id: str) -> None:
    assert session_id != ""
    async with AsyncSessionLocal() as db:
        row = await db.get(OpsWeixinBridge, session_id)
        if row is not None:
            await db.delete(row)
            await db.commit()


async def list_bridges() -> list[PersistedWeixinBridge]:
    """All persisted bridges (``ops_wechat_demo_bridges`` rows) for Ops restart restore."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(OpsWeixinBridge).order_by(OpsWeixinBridge.session_id)
        )
        rows = result.scalars().all()
        return [PersistedWeixinBridge.model_validate(row) for row in rows]
