"""Parse Telegram ``/start`` deep-link payloads for telegram-demo routing."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

_START_CMD = "/start"
_AGENT_PREFIX = "agent_"
_ONBOARD_TOKEN = "onboard"


class StartPayloadKind(StrEnum):
    ONBOARD = "onboard"
    AGENT_ID = "agent_id"
    NONE = "none"


@dataclass(frozen=True)
class StartPayload:
    kind: StartPayloadKind
    agent_id: str | None


@dataclass
class TelegramDemoBinding:
    telegram_chat_id: str
    user_id: str
    agent_id: str
    chat_id: str


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
    """Classify ``/start`` variants: onboard, legacy agent id, or not a start."""
    remainder = _start_remainder(text)
    if remainder is None:
        return StartPayload(kind=StartPayloadKind.NONE, agent_id=None)
    if remainder == "" or remainder == _ONBOARD_TOKEN:
        return StartPayload(kind=StartPayloadKind.ONBOARD, agent_id=None)
    if remainder.startswith(_AGENT_PREFIX):
        agent_id = remainder[len(_AGENT_PREFIX) :].strip()
        if agent_id:
            return StartPayload(
                kind=StartPayloadKind.AGENT_ID,
                agent_id=agent_id,
            )
    return StartPayload(kind=StartPayloadKind.NONE, agent_id=None)


def parse_start_agent_id(text: str) -> str | None:
    """Return ``agent_id`` from ``/start agent_{id}`` or ``/start@bot agent_{id}``."""
    payload = parse_start_payload(text)
    if payload.kind == StartPayloadKind.AGENT_ID:
        return payload.agent_id
    return None
