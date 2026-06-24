"""Twilio Programmable SMS adapter for companion gateway transport.

Generated entirely by Cursor agent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import urlencode

from fastapi import Request

RequestValidatorFactory = Callable[..., Any]
RestClientFactory = Callable[..., Any]


@dataclass(frozen=True)
class TwilioInboundSms:
    """One inbound SMS webhook payload from Twilio."""

    from_e164: str
    to_e164: str
    body: str
    message_sid: str


@dataclass(frozen=True)
class TwilioSmsSendResult:
    """Safe subset of Twilio message create response."""

    sid: str
    status: str


class TwilioSmsApi:
    """Thin wrapper around Twilio Messaging for gateway downlink and webhooks."""

    def __init__(
        self,
        *,
        account_sid: str,
        auth_token: str,
        request_validator_factory: RequestValidatorFactory | None = None,
        rest_client_factory: RestClientFactory | None = None,
    ) -> None:
        assert account_sid != ""
        assert auth_token != ""
        self._account_sid = account_sid
        self._auth_token = auth_token
        self._request_validator_factory = request_validator_factory
        self._rest_client_factory = rest_client_factory

    def send_message(
        self,
        *,
        to_number: str,
        from_number: str,
        body: str,
    ) -> TwilioSmsSendResult:
        assert to_number != ""
        assert from_number != ""
        assert body != ""
        client = self._rest_client(self._account_sid, self._auth_token)
        message = client.messages.create(
            to=to_number,
            from_=from_number,
            body=body,
        )
        return TwilioSmsSendResult(
            sid=str(message.sid),
            status=str(message.status),
        )

    async def validate_webhook(self, *, request: Request, webhook_url: str) -> bool:
        assert webhook_url != ""
        signature = request.headers.get("X-Twilio-Signature", "")
        if signature == "":
            return False
        form = await request.form()
        params = {key: str(value) for key, value in form.items()}
        validator = self._request_validator(self._auth_token)
        return bool(validator.validate(webhook_url, params, signature))

    def _rest_client(self, account_sid: str, auth_token: str) -> Any:
        if self._rest_client_factory is not None:
            return self._rest_client_factory(account_sid, auth_token)
        from twilio.rest import Client

        return Client(account_sid, auth_token)

    def _request_validator(self, auth_token: str) -> Any:
        if self._request_validator_factory is not None:
            return self._request_validator_factory(auth_token)
        from twilio.request_validator import RequestValidator

        return RequestValidator(auth_token)


def parse_inbound_sms_form(form: dict[str, str]) -> TwilioInboundSms:
    """Parse Twilio ``application/x-www-form-urlencoded`` inbound fields."""
    from_e164 = form.get("From", "")
    to_e164 = form.get("To", "")
    body = form.get("Body", "")
    message_sid = form.get("MessageSid", "")
    assert from_e164 != ""
    assert to_e164 != ""
    assert message_sid != ""
    return TwilioInboundSms(
        from_e164=from_e164,
        to_e164=to_e164,
        body=body,
        message_sid=message_sid,
    )


def twilio_empty_response_body() -> str:
    """Return empty TwiML for async SMS webhook handling."""
    return "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response></Response>"


def form_body_for_tests(**fields: str) -> str:
    """Build urlencoded form bodies for webhook tests."""
    return urlencode(fields)
