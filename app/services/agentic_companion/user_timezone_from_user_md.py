"""Backward-compatible re-export; implementation lives in companion harness memory."""

from app.core.companion_harness.memory.user_timezone_from_user_md import (
    infer_iana_timezone_from_user_md,
)

__all__ = ("infer_iana_timezone_from_user_md",)
