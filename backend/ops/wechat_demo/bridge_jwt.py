"""Remint Inty JWT for WeChat demo bridge restore/persist.

Bridge rows store a Bearer JWT for ``WeixinInprocessPresence`` auth. On Ops restart
or Postgres upsert, mint a fresh token from ``Agent.creator_id`` so expired static
JWT does not block restore.
"""

from __future__ import annotations

from dataclasses import dataclass

from jose import JWTError, jwt
from sqlalchemy import select

from app.core.config import global_config_loaded_from_config_yaml
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.models.agent import Agent
from app.models.user import User


class BridgeJwtRemintError(Exception):
    """Bridge JWT cannot be reminted (missing agent/user or JWT/agent mismatch)."""


@dataclass(frozen=True)
class BridgeJwtRemintInput:
    """Inputs to resolve Inty user and mint a bridge JWT."""

    agent_id: str
    inty_jwt: str


def _jwt_sub_unverified(inty_jwt: str) -> str | None:
    """Decode JWT ``sub`` without exp verification; return None if undecodable."""
    assert inty_jwt != ""
    try:
        payload = jwt.decode(
            inty_jwt,
            global_config_loaded_from_config_yaml.security.secret_key,
            algorithms=[
                global_config_loaded_from_config_yaml.security.algorithm
            ],
            options={"verify_exp": False},
        )
    except JWTError:
        return None
    sub = payload.get("sub")
    if sub is None:
        return None
    return str(sub)


async def remint_bridge_inty_jwt(input: BridgeJwtRemintInput) -> str:
    """Mint a fresh access token for the Inty user bound to ``input.agent_id``."""
    assert input.agent_id != ""
    assert input.inty_jwt != ""
    async with AsyncSessionLocal() as db:
        agent = await db.get(Agent, input.agent_id)
        if agent is None:
            raise BridgeJwtRemintError(
                f"wechat_demo bridge jwt remint: agent not found agent_id={input.agent_id}"
            )
        creator_id = agent.creator_id
        assert creator_id != ""
        user_row = await db.execute(
            select(User).where(
                User.id == creator_id,
                User.deleted_at.is_(None),
            )
        )
        user = user_row.scalar_one_or_none()
        if user is None:
            raise BridgeJwtRemintError(
                f"wechat_demo bridge jwt remint: user not found user_id={creator_id}"
            )
    jwt_sub = _jwt_sub_unverified(input.inty_jwt)
    if jwt_sub is not None and jwt_sub != creator_id:
        raise BridgeJwtRemintError(
            "wechat_demo bridge jwt remint: inty_jwt sub does not match agent creator_id"
        )
    return create_access_token(creator_id)
