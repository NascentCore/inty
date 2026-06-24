"""Ops SMS gateway process lifecycle."""

from __future__ import annotations

from loguru import logger

from app.core.config import global_config_loaded_from_config_yaml
from app.external_services.twilio_sms import TwilioSmsApi
from app.utils.config import (
    resolved_sms_from_number,
    resolved_twilio_messaging_credentials,
)
from backend.ops.sms_channel.session_store import restore_persisted_bindings
from backend.ops.sms_channel.transport import SmsTransport

_transport: SmsTransport | None = None


def get_sms_transport() -> SmsTransport | None:
    return _transport


async def start_sms_channel() -> None:
    """Initialize SMS gateway restore when Twilio messaging config is present."""
    global _transport
    from_number = resolved_sms_from_number(
        global_config_loaded_from_config_yaml.agent
    )
    account_sid, auth_token = resolved_twilio_messaging_credentials(
        global_config_loaded_from_config_yaml
    )
    if not from_number or not account_sid or not auth_token:
        logger.info("sms-channel: messaging config incomplete; gateway skipped")
        return
    api = TwilioSmsApi(account_sid=account_sid, auth_token=auth_token)
    await restore_persisted_bindings(api=api, from_number=from_number)
    _transport = SmsTransport(api=api, from_number=from_number)
    logger.info("sms-channel: gateway ready from_number={}", from_number)


async def stop_sms_channel() -> None:
    """Drop in-process SMS transport handle on shutdown."""
    global _transport
    _transport = None
    logger.info("sms-channel: stopped")
