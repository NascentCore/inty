"""Twilio Voice adapter for outbound PSTN calls."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TwilioCallResult:
    """Safe subset of Twilio's call object."""

    sid: str
    status: str


@dataclass
class TwilioPhoneCallService:
    """Thin synchronous wrapper around the official Twilio Python SDK."""

    account_sid: str
    auth_token: str
    from_number: str

    def create_call(self, *, to_number: str, twiml: str) -> TwilioCallResult:
        from twilio.rest import Client

        client = Client(self.account_sid, self.auth_token)
        call = client.calls.create(
            from_=self.from_number,
            to=to_number,
            twiml=twiml,
        )
        return TwilioCallResult(sid=str(call.sid), status=str(call.status))
