"""Prototype helpers for reading boolean flags from ``os.environ``."""

from __future__ import annotations

import os


def env_flag_enabled(name: str) -> bool:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return False
    return str(raw).strip().lower() in ("1", "true", "yes", "on")
