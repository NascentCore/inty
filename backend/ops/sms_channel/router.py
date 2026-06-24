"""FastAPI routes for SMS gateway Twilio webhooks."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request, Response
from loguru import logger

from app.external_services.twilio_sms import (
    parse_inbound_sms_form,
    twilio_empty_response_body,
)
from backend.ops.sms_channel.lifecycle import get_sms_transport

router = APIRouter(prefix="/sms", tags=["sms"])


@router.post("/twilio-inbound", include_in_schema=False)
async def twilio_inbound(request: Request) -> Response:
    """Ack Twilio immediately and process inbound SMS asynchronously."""
    transport = get_sms_transport()
    if transport is None:
        raise HTTPException(status_code=503, detail="SMS gateway is not configured")
    form = await request.form()
    params = {key: str(value) for key, value in form.items()}
    webhook_url = str(request.url.replace(query=""))
    signature = request.headers.get("X-Twilio-Signature", "")
    if not transport.api.validate_webhook_signature(
        webhook_url=webhook_url,
        params=params,
        signature=signature,
    ):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
    inbound = parse_inbound_sms_form(params)

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
