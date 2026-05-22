"""Pydantic models for Ops WeChat self-service demo API."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class WechatDemoSessionPhase(StrEnum):
    QR_LOGIN = "qr_login"
    BRIDGE_RUNNING = "bridge_running"
    STOPPED = "stopped"
    FAILED = "failed"


class WechatDemoSessionCreate(BaseModel):
    inty_api_base_url: str = Field(..., min_length=1)
    inty_jwt: str = Field(..., min_length=1)
    agent_id: str = Field(..., min_length=1)


class WechatDemoSessionView(BaseModel):
    session_id: str
    phase: WechatDemoSessionPhase
    qr_phase: str | None = None
    qrcode_url: str | None = None
    error: str | None = None
    bridge_running: bool = False
