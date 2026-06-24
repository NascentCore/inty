"""FastAPI routes for SMS gateway Twilio webhooks."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request, Response
from loguru import logger
from pydantic import ValidationError

from app.core.config import global_config_loaded_from_config_yaml
from app.external_services.twilio_sms import (
    parse_inbound_sms_form,
    twilio_empty_response_body,
)
from app.utils.config import resolved_sms_twilio_webhook_url
from backend.ops.sms_channel.inbound_dedup import claim_inbound_message_sid
from backend.ops.sms_channel.lifecycle import get_sms_transport

router = APIRouter(prefix="/sms", tags=["sms"])

_TWILIO_INBOUND_PATH = "/api/v1/sms/twilio-inbound"


@router.post("/twilio-inbound", include_in_schema=False)
async def twilio_inbound(request: Request) -> Response:
    """Ack Twilio immediately and process inbound SMS asynchronously."""
    transport = get_sms_transport()
    if transport is None:
        raise HTTPException(status_code=503, detail="SMS gateway is not configured")
    form = await request.form()
    params = {key: str(value) for key, value in form.items()}
    configured_url = resolved_sms_twilio_webhook_url(
        global_config_loaded_from_config_yaml.agent,
        path=_TWILIO_INBOUND_PATH,
    )
    webhook_url = configured_url or str(request.url.replace(query=""))
    signature = request.headers.get("X-Twilio-Signature", "")
    if not transport.api.validate_webhook_signature(
        webhook_url=webhook_url,
        params=params,
        signature=signature,
    ):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
    try:
        inbound = parse_inbound_sms_form(params)
    except ValidationError:
        logger.warning("sms inbound rejected malformed form params={}", params)
        return Response(
            content=twilio_empty_response_body(),
            media_type="application/xml",
        )
    if not claim_inbound_message_sid(inbound.message_sid):
        logger.info(
            "sms inbound duplicate sid={} from={}",
            inbound.message_sid,
            inbound.from_e164,
        )
        return Response(
            content=twilio_empty_response_body(),
            media_type="application/xml",
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
