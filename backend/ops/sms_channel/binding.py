"""Parse inbound SMS command keywords for gateway onboard routing.

Generated entirely by Cursor agent.
"""

from __future__ import annotations

from enum import StrEnum


class SmsCommand(StrEnum):
    """Normalized inbound SMS command."""

    START = "start"
    STOP = "stop"
    CHAT = "chat"


def parse_sms_command(body: str) -> SmsCommand:
    """Classify inbound SMS body after normalization."""
    normalized = " ".join(body.strip().split()).lower()
    match normalized:
        case "start":
            return SmsCommand.START
        case "stop":
            return SmsCommand.STOP
        case _:
            return SmsCommand.CHAT
