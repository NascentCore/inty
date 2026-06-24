"""Process-local Twilio ``MessageSid`` dedup for inbound SMS webhooks.

Prototype: in-memory only; clears on Ops restart. Production scale needs Postgres/Redis (#3351).
"""

from __future__ import annotations

_MAX_SEEN_SIDS = 10_000

_seen_message_sids: set[str] = set()


def claim_inbound_message_sid(message_sid: str) -> bool:
    """Return True when ``message_sid`` is new and should be processed."""
    assert message_sid != ""
    if message_sid in _seen_message_sids:
        return False
    _seen_message_sids.add(message_sid)
    if len(_seen_message_sids) > _MAX_SEEN_SIDS:
        _seen_message_sids.clear()
    return True


def clear_inbound_dedup_for_tests() -> None:
    _seen_message_sids.clear()
