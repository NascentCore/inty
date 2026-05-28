"""Turn-level implicit signals from client / runtime (companion MVP: client time)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.chat import UserTimeContext


class HumanChannel(StrEnum):
    """Human-facing channel that produced this companion turn."""

    UNKNOWN = "unknown"
    APP = "app"
    WECHAT = "wechat"
    WEIXIN = "weixin"


class ImplicitSignalBundle(BaseModel):
    """Versioned bundle for telemetry injected alongside user turns (not user-authored text)."""

    schema_version: Literal[1] = Field(
        default=1, description="Bump when adding breaking fields."
    )
    client_time: Optional[UserTimeContext] = None
    user_signed_on: bool = Field(
        default=False,
        description="Client implicit signal: user came online; prompts may ask for a brief greeting.",
    )
    human_channel: HumanChannel = Field(
        default=HumanChannel.UNKNOWN,
        description="Human-facing channel for this turn; prompt clauses may be channel-specific.",
    )
    server_received_at_utc: Optional[datetime] = Field(
        default=None,
        description="Server receipt time; not rendered into prompts in MVP.",
    )
