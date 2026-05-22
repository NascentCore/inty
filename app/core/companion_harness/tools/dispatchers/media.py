"""Shared argument parsers for companion media tools.

Image generation and editing accept model-facing JSON arguments before the
provider adapter runs. These helpers validate the small numeric payload fields
that affect media requests and return user-visible error text for the tool loop.
"""

from __future__ import annotations

from typing import Any


def parse_optional_positive_int(
    raw: Any,
    *,
    field_name: str,
) -> tuple[int | None, str | None]:
    """Parse optional positive integer payload fields for media requests."""
    if raw is None:
        return (None, None)
    if isinstance(raw, bool):
        return (None, f"{field_name} must be an integer")
    if isinstance(raw, int):
        if raw < 1:
            return (None, f"{field_name} must be >= 1")
        return (raw, None)
    return (None, f"{field_name} must be an integer")


def parse_optional_strength(raw: Any) -> tuple[float | None, str | None]:
    """Parse optional image-edit strength as a closed interval from 0 to 1."""
    if raw is None:
        return (None, None)
    if isinstance(raw, bool):
        return (None, "strength must be a number")
    if isinstance(raw, (int, float)):
        parsed = float(raw)
        if not (0.0 <= parsed <= 1.0):
            return (None, "strength must be between 0 and 1 inclusive")
        return (parsed, None)
    return (None, "strength must be a number")
