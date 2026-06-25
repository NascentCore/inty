"""Parse Telegram ``/start`` deep-link payloads for Telegram channel routing."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

_START_CMD = "/start"
_ONBOARD_TOKEN = "onboard"


class StartPayloadKind(StrEnum):
    ONBOARD = "onboard"
    NONE = "none"


@dataclass(frozen=True)
class StartPayload:
    kind: StartPayloadKind


def _start_remainder(text: str) -> str | None:
    assert text is not None
    stripped = text.strip()
    if not stripped.startswith(_START_CMD):
        return None
    remainder = stripped[len(_START_CMD) :].strip()
    if remainder.startswith("@"):
        space_idx = remainder.find(" ")
        if space_idx < 0:
            return ""
        remainder = remainder[space_idx + 1 :].strip()
    return remainder


def parse_start_payload(text: str) -> StartPayload:
    """Classify ``/start`` variants that trigger Telegram channel onboard."""
    remainder = _start_remainder(text)
    if remainder is None:
        return StartPayload(kind=StartPayloadKind.NONE)
    if remainder == "" or remainder == _ONBOARD_TOKEN:
        return StartPayload(kind=StartPayloadKind.ONBOARD)
    return StartPayload(kind=StartPayloadKind.NONE)
