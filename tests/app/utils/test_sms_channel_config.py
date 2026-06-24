"""SMS channel config helpers."""

from __future__ import annotations

from app.utils.config import (
    AgentChannelsConfig,
    AgentConfig,
    SmsChannelConfig,
    resolved_sms_twilio_webhook_url,
)


def test_resolved_sms_twilio_webhook_url_empty_base() -> None:
    agent = AgentConfig(
        api_key="test",
        langchain_api_key="test",
        channels=AgentChannelsConfig(sms=SmsChannelConfig()),
    )
    assert resolved_sms_twilio_webhook_url(
        agent,
        path="/api/v1/sms/twilio-inbound",
    ) == ""


def test_resolved_sms_twilio_webhook_url_joins_base_and_path() -> None:
    agent = AgentConfig(
        api_key="test",
        langchain_api_key="test",
        channels=AgentChannelsConfig(
            sms=SmsChannelConfig(
                webhook_base_url="https://ops.example.com/",
            )
        )
    )
    assert resolved_sms_twilio_webhook_url(
        agent,
        path="/api/v1/sms/twilio-inbound",
    ) == "https://ops.example.com/api/v1/sms/twilio-inbound"
