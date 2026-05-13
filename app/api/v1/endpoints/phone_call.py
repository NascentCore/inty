"""Phone-call HTTP and Twilio Media Streams endpoints."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket
from loguru import logger
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.schemas.live_chat import LiveChatConfig, LiveChatStatus
from app.schemas.phone_call import (
    PhoneCallInboundWebhookRequest,
    PhoneCallStartRequest,
)
from app.schemas.response import APIResponse
from app.schemas.user import User as UserSchema
from app.services.global_services import subscription_service
from app.services.live_chat_service import live_chat_service
from app.services.phone_call_service import (
    PhoneCallConfigError,
    PhoneCallLimitError,
    TwilioPcmBridgeCodec,
    phone_call_service,
)

router = APIRouter(prefix="/phone-calls")


@router.get("/status")
async def get_phone_call_status(
    current_user: UserSchema = Depends(deps.get_current_active_user),
):
    _ = current_user
    return APIResponse.success(data=phone_call_service.status().model_dump())


@router.post("/{agent_id}")
async def start_phone_call(
    *,
    agent_id: str,
    request: PhoneCallStartRequest,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: UserSchema = Depends(deps.get_current_active_user),
):
    try:
        result = await phone_call_service.start_outbound_call(
            db=db,
            current_user=current_user,
            agent_id=agent_id,
            phone_number=request.phone_number,
            subscription_svc=subscription_service,
            speech_language_code=request.speech_language_code,
            response_language_name=request.response_language_name,
            reason="explicit_api_request",
        )
    except PhoneCallLimitError as exc:
        return exc.error_response
    except PhoneCallConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return APIResponse.success(data=result.model_dump())


@router.post("/twilio/inbound")
async def twilio_inbound_call(
    request: Request,
    db: AsyncSession = Depends(deps.get_async_db),
):
    form = await request.form()
    try:
        inbound = PhoneCallInboundWebhookRequest.model_validate(dict(form))
    except ValidationError as exc:
        logger.warning("invalid Twilio inbound webhook: {}", exc)
        twiml = phone_call_service.build_reject_twiml("Invalid phone-call request.")
    else:
        twiml = await phone_call_service.build_inbound_twiml(db=db, inbound=inbound)
    return Response(content=twiml, media_type="application/xml")


@router.websocket("/twilio-media")
async def twilio_media_stream(
    websocket: WebSocket,
    db: AsyncSession = Depends(deps.get_async_db),
):
    token = (websocket.query_params.get("token") or "").strip()
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return
    try:
        payload = phone_call_service.verify_media_token(token)
    except ValueError:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await websocket.accept()
    codec = TwilioPcmBridgeCodec()
    stream_sid: Optional[str] = None
    session = None
    session_start = time.time()
    input_queue: asyncio.Queue[Optional[dict]] = asyncio.Queue()

    try:
        live_config = LiveChatConfig(
            speech_language_code=payload.speech_language_code,
            response_language_name=payload.response_language_name,
            agent_starts_conversation=True,
        )
        session = await live_chat_service.create_session(
            db=db,
            agent_id=payload.agent_id,
            user_id=payload.sub,
            config=live_config,
        )

        async def on_audio(data: bytes) -> None:
            if not stream_sid:
                return
            twilio_payload = codec.pcm16_24k_to_twilio_mulaw_8k_payload(data)
            await websocket.send_json(
                {
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {"payload": twilio_payload},
                }
            )

        async def on_transcript(
            text: str,
            role: str,
            message_id: Optional[int] = None,
            timestamp: Optional[float] = None,
        ) -> None:
            _ = text, role, message_id, timestamp

        async def on_status(status: LiveChatStatus, message: Optional[str]) -> None:
            _ = status, message

        async def on_error(
            error_code: str, message: str, code: Optional[int] = None
        ) -> None:
            logger.warning(
                "phone_call twilio media live error code={} business_code={} message={}",
                error_code,
                code,
                message,
            )

        async def on_latency(latency_data: dict) -> None:
            _ = latency_data

        live_gen = live_chat_service.start_live_session(
            session=session,
            db=db,
            on_audio=on_audio,
            on_transcript=on_transcript,
            on_status=on_status,
            on_error=on_error,
            on_latency=on_latency,
        )

        async def send_audio_loop() -> None:
            try:
                await live_gen.asend(None)
                while True:
                    item = await input_queue.get()
                    if item is None:
                        break
                    await live_gen.asend(item)
            except StopAsyncIteration:
                pass
            finally:
                try:
                    await live_gen.aclose()
                except RuntimeError:
                    pass

        send_task = asyncio.create_task(send_audio_loop())
        try:
            while True:
                raw = await websocket.receive_text()
                frame = json.loads(raw)
                event = frame.get("event")
                if event == "start":
                    stream_sid = frame.get("streamSid") or frame.get("start", {}).get(
                        "streamSid"
                    )
                elif event == "media":
                    media = frame.get("media") or {}
                    media_payload = media.get("payload")
                    if isinstance(media_payload, str):
                        pcm16 = codec.twilio_mulaw_8k_to_pcm16_16k(media_payload)
                        await input_queue.put({"type": "audio", "data": pcm16})
                elif event == "stop":
                    await input_queue.put(None)
                    break
        finally:
            await input_queue.put(None)
            send_task.cancel()
            try:
                await send_task
            except asyncio.CancelledError:
                pass

    except Exception as exc:
        logger.warning("phone_call Twilio media stream failed: {}", exc)
    finally:
        duration = int(time.time() - session_start)
        if session:
            await live_chat_service.end_session(session.session_id)
        if duration > 0:
            try:
                await subscription_service.record_usage(
                    db=None,
                    user_id=payload.sub,
                    usage_type="live_chat",
                    usage_count=1,
                    extra_data={
                        "agent_id": payload.agent_id,
                        "duration_seconds": duration,
                        "channel": "phone_call",
                        "direction": payload.direction,
                        "twilio_call_sid": payload.call_sid,
                    },
                )
            except Exception as exc:
                logger.warning("phone_call usage record failed: {}", exc)
        try:
            await websocket.close()
        except RuntimeError:
            pass
