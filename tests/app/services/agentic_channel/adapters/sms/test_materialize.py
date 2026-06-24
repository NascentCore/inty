"""Tests for SMS body materialization."""

from __future__ import annotations

from app.services.agentic_channel.adapters.sms.materialize import materialize_sms_body


def test_materialize_sms_body_strips_markdown_and_segments() -> None:
    text = "**Hello** " + ("x" * 200)
    segments = materialize_sms_body(text)
    assert segments[0].startswith("Hello ")
    assert sum(len(segment) for segment in segments) >= 200


def test_materialize_sms_body_empty() -> None:
    assert materialize_sms_body("   ") == ()
