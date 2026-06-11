"""Parse Telegram ``/start`` deep-link payloads for telegram-demo routing."""

from __future__ import annotations

from dataclasses import dataclass

_START_CMD = "/start"
_AGENT_PREFIX = "agent_"


@dataclass
class TelegramDemoBinding:
    telegram_chat_id: str
    user_id: str
    agent_id: str
    chat_id: str


def parse_start_agent_id(text: str) -> str | None:
    """Return ``agent_id`` from ``/start agent_{id}`` or ``/start@bot agent_{id}``."""
    assert text is not None
    stripped = text.strip()
    if not stripped.startswith(_START_CMD):
        return None
    remainder = stripped[len(_START_CMD) :].strip()
    if remainder.startswith("@"):
        space_idx = remainder.find(" ")
        if space_idx < 0:
            return None
        remainder = remainder[space_idx + 1 :].strip()
    if not remainder.startswith(_AGENT_PREFIX):
        return None
    agent_id = remainder[len(_AGENT_PREFIX) :].strip()
    if not agent_id:
        return None
    return agent_id
