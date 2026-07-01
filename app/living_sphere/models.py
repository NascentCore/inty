"""LivingSphere change log rows and tool constants for companion MemoryStore."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator


def _new_update_id() -> str:
    return uuid.uuid4().hex


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class LivingSphereUpdate(BaseModel):
    """One user-directed LivingSphere change intent (append-only jsonl row)."""

    update_id: str = Field(default_factory=_new_update_id)
    created_at_utc: str = Field(default_factory=_utc_now_iso)
    change_request: str
    source: str = Field(
        default="chat_tool",
        description="Origin surface, e.g. chat_tool vs future offline_batch.",
    )
    user_msg_uuid: str | None = None
    trace_id: str | None = None

    @field_validator("update_id", "created_at_utc", "change_request", "source")
    @classmethod
    def _strip_required_text(cls, value: str) -> str:
        out = value.strip()
        if not out:
            raise ValueError("field must be non-empty")
        return out

    @field_validator("user_msg_uuid", "trace_id")
    @classmethod
    def _strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        out = value.strip()
        return out or None


LIVING_SPHERE_RECORD_UPDATE_TOOL_NAME = "living_sphere_record_update"
