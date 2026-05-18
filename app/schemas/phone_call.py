"""Pydantic contracts for PSTN phone-call APIs and Twilio webhooks."""

from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.live_chat import LiveChatConfig

_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")


class PhoneCallStartRequest(BaseModel):
    """Request to place an outbound PSTN call for an agent."""

    phone_number: str = Field(
        ...,
        description="Destination phone number, E.164 or local digits normalizable by the server.",
    )
    speech_language_code: Optional[str] = Field(
        default=None,
        description="Optional BCP-47 speech language override for the phone-call session.",
    )
    response_language_name: Optional[str] = Field(
        default=None,
        description="Optional English-readable response language override.",
    )

    @field_validator("phone_number", mode="before")
    @classmethod
    def normalize_phone_number_text(cls, v: object) -> str:
        s = str(v).strip()
        if not s:
            raise ValueError("phone_number is required")
        return s

    @field_validator("speech_language_code")
    @classmethod
    def validate_speech_language_code(cls, v: Optional[str]) -> Optional[str]:
        return LiveChatConfig(speech_language_code=v).speech_language_code

    @field_validator("response_language_name")
    @classmethod
    def validate_response_language_name(cls, v: Optional[str]) -> Optional[str]:
        return LiveChatConfig(response_language_name=v).response_language_name


class PhoneCallStartResponse(BaseModel):
    """Safe outbound-call response returned to authenticated clients."""

    call_sid: str
    status: str
    agent_id: str
    to_number_masked: str


class PhoneCallStatusResponse(BaseModel):
    """Phone-call capability status without exposing provider secrets."""

    enabled: bool
    available: bool
    twilio_configured: bool
    media_stream_configured: bool
    live_chat_enabled: bool
    from_number_configured: bool


class PhoneCallInboundWebhookRequest(BaseModel):
    """Subset of Twilio inbound Voice webhook form fields used by Inty."""

    from_number: str = Field(alias="From")
    to_number: str = Field(alias="To")
    call_sid: str = Field(alias="CallSid")


class PhoneCallMediaTokenPayload(BaseModel):
    """Signed short-lived token payload for Twilio Media Streams."""

    sub: str
    agent_id: str
    chat_id: Optional[str] = None
    direction: str
    jti: str
    call_sid: Optional[str] = None
    speech_language_code: Optional[str] = None
    response_language_name: Optional[str] = None
    exp: int


def is_e164_phone_number(value: str) -> bool:
    return bool(_E164_RE.fullmatch(value.strip()))
