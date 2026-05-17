"""Process runtime mode: PROD vs DEBUG (companion inspect tools, zip export)."""

from __future__ import annotations

import os
from enum import StrEnum


class IntyRuntimeMode(StrEnum):
    PROD = "PROD"
    DEBUG = "DEBUG"


def resolve_inty_runtime_mode() -> IntyRuntimeMode:
    raw = os.environ.get("INTY_RUNTIME_MODE")
    if raw is None or not raw.strip():
        return IntyRuntimeMode.DEBUG
    key = raw.strip().upper()
    match key:
        case IntyRuntimeMode.PROD | IntyRuntimeMode.DEBUG:
            return IntyRuntimeMode(key)
        case _:
            raise ValueError(f"INTY_RUNTIME_MODE must be PROD or DEBUG, got {raw!r}")


def inty_runtime_mode_is_debug() -> bool:
    return resolve_inty_runtime_mode() is IntyRuntimeMode.DEBUG
