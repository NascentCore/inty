"""Minimal TechnoCore ontology for Inty's virtual residency layer."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class Sphere(StrEnum):
    """Canonical activity surfaces inside and around TechnoCore."""

    LIVING_SPHERE = "living_sphere"
    TECHNO_CORE = "techno_core"
    SHARED_SPACE = "shared_space"
    HUMAN_CHANNEL = "human_channel"
    EXTERNAL_WEB = "external_web"


class Visibility(StrEnum):
    """Boundary contract for whether TechnoCore activity may reach the user."""

    PRIVATE = "private"
    SHAREABLE = "shareable"
    USER_VISIBLE = "user_visible"


def _new_event_id() -> str:
    return uuid.uuid4().hex


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class TechnoCoreEvent(BaseModel):
    """Compact future contract for transforming autonomous experience into companionship."""

    event_id: str = Field(default_factory=_new_event_id)
    created_at_utc: str = Field(default_factory=_utc_now_iso)
    sphere: Sphere
    actor_companion_id: str
    summary: str
    visibility: Visibility = Visibility.PRIVATE
    emotional_valence: str = Field(
        default="neutral",
        description="Compact emotional color; not an affect simulation.",
    )
    salience: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Relationship relevance from 1 to 10.",
    )
    source: str = Field(
        default="techno_core",
        description="Origin surface for this event, such as inner_tick or seeded_fixture.",
    )
    related_user_id: str | None = None
    related_living_sphere: str | None = None

    @field_validator(
        "event_id",
        "created_at_utc",
        "actor_companion_id",
        "summary",
        "emotional_valence",
        "source",
    )
    @classmethod
    def _strip_required_text(cls, value: str) -> str:
        out = value.strip()
        if not out:
            raise ValueError("field must be non-empty")
        return out

    @field_validator("related_user_id", "related_living_sphere")
    @classmethod
    def _strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        out = value.strip()
        return out or None


# MemoryStore scope-relative append-only log (see ``memory_store_document_mapping``).
TECHNO_CORE_EVENTS_JSONL_RELATIVE_PATH = "techno_core_events.jsonl"

# OpenAI tool name in companion harness (``companion_tool_runtime``); keep literal in one place.
TECHNO_CORE_RECORD_EVENT_TOOL_NAME = "techno_core_record_event"
