"""Tests for Twilio SMS webhook signature validation."""

from __future__ import annotations

import pytest

from app.external_services.twilio_sms import TwilioSmsApi, parse_inbound_sms_form


class _FakeValidator:
    def __init__(self, *, valid: bool) -> None:
        self._valid = valid
        self.calls: list[tuple[str, dict[str, str], str]] = []

    def validate(self, url: str, params: dict[str, str], signature: str) -> bool:
        self.calls.append((url, params, signature))
        return self._valid


def test_parse_inbound_sms_form_from_pydantic() -> None:
    inbound = parse_inbound_sms_form(
        {
            "From": "+11234560123",
            "To": "+15005550006",
            "Body": "hello",
            "MessageSid": "SM123",
        }
    )
    assert inbound.from_e164 == "+11234560123"
    assert inbound.body == "hello"


def test_validate_webhook_signature_delegates_to_validator() -> None:
    validator = _FakeValidator(valid=True)
    api = TwilioSmsApi(
        account_sid="AC_TEST",
        auth_token="auth",
        request_validator_factory=lambda _token: validator,
    )
    params = {"From": "+1", "To": "+2", "MessageSid": "SM1"}
    assert api.validate_webhook_signature(
        webhook_url="https://ops.example/api/v1/sms/twilio-inbound",
        params=params,
        signature="sig",
    )
    assert validator.calls == [
        (
            "https://ops.example/api/v1/sms/twilio-inbound",
            params,
            "sig",
        )
    ]


def test_validate_webhook_signature_rejects_empty_signature() -> None:
    api = TwilioSmsApi(account_sid="AC_TEST", auth_token="auth")
    assert not api.validate_webhook_signature(
        webhook_url="https://ops.example/hook",
        params={},
        signature="",
    )
