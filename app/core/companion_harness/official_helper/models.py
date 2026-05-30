"""Value objects for official helper turns."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class OfficialHelperReason(StrEnum):
    """Why the companion path was bypassed for this user-visible helper reply."""

    DREAMING = "dreaming"
    APP_HELP = "app_help"
    SYSTEM_MALFUNCTION = "system_malfunction"


class OfficialHelperRequest(BaseModel):
    """Inputs for one official helper user-chat short-circuit."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reason: OfficialHelperReason
    companion_display_name: str = Field(min_length=1, description="The display name of the companion.")
    user_msg_uuid: str = Field(min_length=1, description="The UUID of the user message that triggered the official helper.")
