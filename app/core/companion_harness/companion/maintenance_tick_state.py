"""Persisted subjective clock for maintenance inner-tick.

The WebSocket/Weixin presence drives maintenance with an in-process monotonic
clock that resets on every reconnect, so an offline companion has no sense of
elapsed wall-clock time. This module persists the last maintenance fire as a
MemoryStore document (``.companion_maintenance_tick_state.json``), giving the
offline scheduler a cross-connection / cross-restart throttle anchor.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)


class MaintenanceTickState(BaseModel):
    """Throttle anchor for offline maintenance: last fire time + transcript size then."""

    last_fired_at_utc: datetime = Field(
        ...,
        description="tz-aware UTC timestamp of the last successful maintenance fire",
    )
    last_transcript_line_count: int = Field(
        ...,
        ge=0,
        description="maintenance-gate transcript line count observed at last fire",
    )


def _document_rel() -> str:
    return DEFAULT_MEMORY_STORE_SCOPE_PATHS.maintenance_tick_state_json


def load_maintenance_tick_state(
    store: MemoryStore,
) -> MaintenanceTickState | None:
    """Read the persisted maintenance tick state, or ``None`` when absent/empty."""
    body = store.read_document_if_exists(_document_rel())
    if body is None or not body.strip():
        return None
    return MaintenanceTickState.model_validate_json(body)


def save_maintenance_tick_state(
    store: MemoryStore, state: MaintenanceTickState
) -> None:
    """Persist the maintenance tick state as the scope document (ISO datetime)."""
    store.write_document(
        _document_rel(), state.model_dump_json(indent=2) + "\n"
    )
