"""Pydantic models for Ops Weixin onboard session API.

TODO(weixin-onboard-jwt-delivery): Do not return long-lived JWT on public GET poll.
Use one-time exchange code (POST redeem) or deliver after QR confirmed via WeChat DM only.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class WeixinSessionPhase(StrEnum):
    QR_LOGIN = "qr_login"
    BRIDGE_RUNNING = "bridge_running"
    STOPPED = "stopped"
    FAILED = "failed"


class WeixinOnboardSessionCreate(BaseModel):
    """Start Weixin onboard session (QR only; user/agent provisioned after scan)."""

    inty_api_base_url: str = Field(..., min_length=1)

    @field_validator("inty_api_base_url", mode="before")
    @classmethod
    def _strip_api_base(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        out = value.strip()
        if not out:
            raise ValueError("field must be non-empty")
        return out


class WeixinSessionView(BaseModel):
    session_id: str
    phase: WeixinSessionPhase
    qr_phase: str | None = None
    qrcode_url: str | None = None
    error: str | None = None
    bridge_running: bool = False
    agent_id: str | None = None
    is_new_user: bool | None = None
