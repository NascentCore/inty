"""FastAPI routes for SMS gateway Twilio webhooks."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request, Response
from loguru import logger

from app.core.config import global_config_loaded_from_config_yaml
from app.external_services.twilio_sms import (
    parse_inbound_sms_form,
    twilio_empty_response_body,
)
from app.utils.config import (
    resolved_sms_from_number,
    resolved_twilio_messaging_credentials,
)
from backend.ops.sms_channel.lifecycle import get_sms_transport

router = APIRouter(prefix="/sms", tags=["sms"])


@router.post("/twilio-inbound", include_in_schema=False)
async def twilio_inbound(request: Request) -> Response:
    """Ack Twilio immediately and process inbound SMS asynchronously."""
    transport = get_sms_transport()
    if transport is None:
        raise HTTPException(status_code=503, detail="SMS gateway is not configured")
    account_sid, auth_token = resolved_twilio_messaging_credentials(
        global_config_loaded_from_config_yaml
    )
    from_number = resolved_sms_from_number(
        global_config_loaded_from_config_yaml.agent
    )
    if not account_sid or not auth_token or not from_number:
        raise HTTPException(status_code=503, detail="SMS gateway is not configured")
    from app.external_services.twilio_sms import TwilioSmsApi

    api = TwilioSmsApi(account_sid=account_sid, auth_token=auth_token)
    webhook_url = str(request.url.replace(query=""))
    if not await api.validate_webhook(request=request, webhook_url=webhook_url):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
    form = await request.form()
    inbound = parse_inbound_sms_form(
        {key: str(value) for key, value in form.items()}
    )

    async def _process() -> None:
        try:
            await transport.handle_inbound(inbound)
        except Exception:
            logger.exception(
                "sms inbound processing failed from={} sid={}",
                inbound.from_e164,
                inbound.message_sid,
            )

    asyncio.create_task(_process())
    return Response(
        content=twilio_empty_response_body(),
        media_type="application/xml",
    )
