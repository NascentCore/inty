"""Inbound Twilio MessageSid dedup for SMS webhooks."""

from __future__ import annotations

from backend.ops.sms_channel.inbound_dedup import (
    claim_inbound_message_sid,
    clear_inbound_dedup_for_tests,
)


def test_claim_inbound_message_sid_accepts_first_seen() -> None:
    clear_inbound_dedup_for_tests()
    assert claim_inbound_message_sid("SM_FIRST") is True


def test_claim_inbound_message_sid_rejects_duplicate() -> None:
    clear_inbound_dedup_for_tests()
    assert claim_inbound_message_sid("SM_DUP") is True
    assert claim_inbound_message_sid("SM_DUP") is False
