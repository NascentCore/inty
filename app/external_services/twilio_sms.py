"""Twilio Programmable SMS adapter for companion gateway transport.

Generated entirely by Cursor agent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import urlencode

from pydantic import BaseModel, ConfigDict, Field

RequestValidatorFactory = Callable[..., Any]
RestClientFactory = Callable[..., Any]


@dataclass(frozen=True)
class TwilioInboundSms:
    """Normalized inbound SMS after Twilio webhook validation."""

    from_e164: str
    to_e164: str
    body: str
    message_sid: str


@dataclass(frozen=True)
class TwilioSmsSendResult:
    """Safe subset of Twilio message create response."""

    sid: str
    status: str


class TwilioInboundSmsForm(BaseModel):
    """Twilio ``application/x-www-form-urlencoded`` inbound SMS fields."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    from_e164: str = Field(validation_alias="From", description="Sender E.164")
    to_e164: str = Field(validation_alias="To", description="Long code E.164")
    body: str = Field(default="", validation_alias="Body", description="SMS body")
    message_sid: str = Field(
        validation_alias="MessageSid",
        description="Twilio message sid",
    )


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

    def validate_webhook_signature(
        self,
        *,
        webhook_url: str,
        params: dict[str, str],
        signature: str,
    ) -> bool:
        """Return whether ``signature`` matches Twilio webhook params."""
        assert webhook_url != ""
        if signature == "":
            return False
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


def parse_inbound_sms_form(params: dict[str, str]) -> TwilioInboundSms:
    """Parse Twilio inbound webhook form fields."""
    form = TwilioInboundSmsForm.model_validate(params)
    assert form.from_e164 != ""
    assert form.to_e164 != ""
    assert form.message_sid != ""
    return TwilioInboundSms(
        from_e164=form.from_e164,
        to_e164=form.to_e164,
        body=form.body,
        message_sid=form.message_sid,
    )


def twilio_empty_response_body() -> str:
    """Return empty TwiML for async SMS webhook handling."""
    return "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response></Response>"


def form_body_for_tests(**fields: str) -> str:
    """Build urlencoded form bodies for webhook tests."""
    return urlencode(fields)
