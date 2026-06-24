"""SMS Twilio inbound webhook route."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.external_services.twilio_sms import TwilioInboundSms
from backend.ops.main import app
from backend.ops.sms_channel.inbound_dedup import clear_inbound_dedup_for_tests
from backend.ops.sms_channel.transport import SmsTransport

_INBOUND_URL = "/api/v1/sms/twilio-inbound"
_FORM = {
    "From": "+11234560123",
    "To": "+15005550006",
    "Body": "hello",
    "MessageSid": "SM_ROUTER_1",
}


class _FakeTwilioSmsApi:
    def validate_webhook_signature(
        self,
        *,
        webhook_url: str,
        params: dict[str, str],
        signature: str,
    ) -> bool:
        assert webhook_url != ""
        assert signature == "sig"
        return True


@pytest.fixture(autouse=True)
def _clear_dedup() -> None:
    clear_inbound_dedup_for_tests()


def test_twilio_inbound_returns_503_when_transport_missing() -> None:
    with patch(
        "backend.ops.sms_channel.router.get_sms_transport",
        return_value=None,
    ):
        client = TestClient(app)
        response = client.post(
            _INBOUND_URL,
            data=_FORM,
            headers={"X-Twilio-Signature": "sig"},
        )
    assert response.status_code == 503


def test_twilio_inbound_uses_configured_webhook_url_for_signature() -> None:
    transport = SmsTransport(
        api=_FakeTwilioSmsApi(),  # type: ignore[arg-type]
        from_number="+15005550006",
    )
    with (
        patch(
            "backend.ops.sms_channel.router.get_sms_transport",
            return_value=transport,
        ),
        patch(
            "backend.ops.sms_channel.router.resolved_sms_twilio_webhook_url",
            return_value="https://public.ops.example/api/v1/sms/twilio-inbound",
        ),
        patch.object(
            transport,
            "handle_inbound",
            new_callable=AsyncMock,
        ) as handle_inbound,
        patch(
            "backend.ops.sms_channel.router.claim_inbound_message_sid",
            return_value=True,
        ),
    ):
        client = TestClient(app)
        response = client.post(
            _INBOUND_URL,
            data=_FORM,
            headers={"X-Twilio-Signature": "sig"},
        )
    assert response.status_code == 200
    assert "application/xml" in response.headers.get("content-type", "")
    handle_inbound.assert_awaited_once()


def test_twilio_inbound_skips_duplicate_message_sid() -> None:
    transport = MagicMock(spec=SmsTransport)
    transport.api = _FakeTwilioSmsApi()
    transport.handle_inbound = AsyncMock()
    with patch(
        "backend.ops.sms_channel.router.get_sms_transport",
        return_value=transport,
    ):
        client = TestClient(app)
        first = client.post(
            _INBOUND_URL,
            data=_FORM,
            headers={"X-Twilio-Signature": "sig"},
        )
        second = client.post(
            _INBOUND_URL,
            data=_FORM,
            headers={"X-Twilio-Signature": "sig"},
        )
    assert first.status_code == 200
    assert second.status_code == 200
    assert transport.handle_inbound.await_count == 1


def test_twilio_inbound_malformed_form_returns_empty_twiml() -> None:
    transport = MagicMock(spec=SmsTransport)
    transport.api = _FakeTwilioSmsApi()
    with patch(
        "backend.ops.sms_channel.router.get_sms_transport",
        return_value=transport,
    ):
        client = TestClient(app)
        response = client.post(
            _INBOUND_URL,
            data={"From": "+1"},
            headers={"X-Twilio-Signature": "sig"},
        )
    assert response.status_code == 200
    transport.handle_inbound.assert_not_called()
