"""Phone-call orchestration across Twilio PSTN and existing Gemini Live sessions."""

from __future__ import annotations

import audioop
import base64
import hashlib
import hmac
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode
from xml.sax.saxutils import escape as xml_escape

from jose import JWTError, jwt
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import global_config_loaded_from_config_yaml
from app.external_services.twilio_phone_call import (
    TwilioCallResult,
    TwilioPhoneCallService,
)
from app.models.phone_call import PhoneCallCallerBinding
from app.schemas import User
from app.schemas.live_chat import LiveChatConfig
from app.schemas.phone_call import (
    PhoneCallInboundWebhookRequest,
    PhoneCallMediaTokenPayload,
    PhoneCallStartResponse,
    PhoneCallStatusResponse,
    is_e164_phone_number,
)
from app.schemas.response import BusinessErrorCode, create_business_error_response
from app.services.subscription_service import SubscriptionService

_PHONE_DIGITS_RE = re.compile(r"\d+")
_CALL_ME_AT_RE = re.compile(
    r"\bcall\s+me\s+at\s+(?P<number>\+?[\d][\d\s().-]{6,}[\d])\b",
    flags=re.IGNORECASE,
)


class PhoneCallConfigError(RuntimeError):
    """Raised when phone-call dependencies are unavailable."""


class PhoneCallLimitError(RuntimeError):
    """Raised when existing live-chat quota blocks a phone call."""

    def __init__(self, error_response: dict[str, Any]) -> None:
        super().__init__(str(error_response.get("message") or "Phone call limit reached"))
        self.error_response = error_response


@dataclass
class ResampleState:
    """State for streaming audioop.ratecv conversion."""

    state: object | None = None


@dataclass
class TwilioPcmBridgeCodec:
    """Twilio μ-law 8k ⇄ Gemini PCM16 helpers with resampler state."""

    inbound_state: ResampleState = field(default_factory=ResampleState)
    outbound_state: ResampleState = field(default_factory=ResampleState)

    def twilio_mulaw_8k_to_pcm16_16k(self, payload_b64: str) -> bytes:
        mulaw = base64.b64decode(payload_b64)
        pcm8 = audioop.ulaw2lin(mulaw, 2)
        pcm16, self.inbound_state.state = audioop.ratecv(
            pcm8,
            2,
            1,
            8000,
            16000,
            self.inbound_state.state,
        )
        return pcm16

    def pcm16_24k_to_twilio_mulaw_8k_payload(self, pcm24: bytes) -> str:
        pcm8, self.outbound_state.state = audioop.ratecv(
            pcm24,
            2,
            1,
            24000,
            8000,
            self.outbound_state.state,
        )
        mulaw = audioop.lin2ulaw(pcm8, 2)
        return base64.b64encode(mulaw).decode("ascii")


class PhoneCallService:
    """Business service for outbound calls, inbound TwiML, and media tokens."""

    def __init__(self) -> None:
        self.config = global_config_loaded_from_config_yaml.phone_call
        self.security = global_config_loaded_from_config_yaml.security
        self.gemini_live_config = global_config_loaded_from_config_yaml.gemini_live

    @property
    def account_sid(self) -> str:
        return (
            os.environ.get("TWILIO_ACCOUNT_SID")
            or self.config.twilio_account_sid
            or ""
        ).strip()

    @property
    def auth_token(self) -> str:
        return (
            os.environ.get("TWILIO_AUTH_TOKEN")
            or self.config.twilio_auth_token
            or ""
        ).strip()

    @property
    def from_number(self) -> str:
        return (
            os.environ.get("TWILIO_PHONE_NUMBER")
            or self.config.twilio_from_number
            or ""
        ).strip()

    @property
    def media_stream_base_url(self) -> str:
        return (self.config.twilio_media_stream_base_url or "").strip().rstrip("/")

    def status(self) -> PhoneCallStatusResponse:
        twilio_configured = bool(self.account_sid and self.auth_token)
        media_configured = bool(self.media_stream_base_url.startswith("wss://"))
        from_configured = bool(self.from_number)
        live_enabled = bool(self.gemini_live_config.enabled)
        return PhoneCallStatusResponse(
            enabled=bool(self.config.enabled),
            available=bool(
                self.config.enabled
                and twilio_configured
                and media_configured
                and from_configured
                and live_enabled
            ),
            twilio_configured=twilio_configured,
            media_stream_configured=media_configured,
            live_chat_enabled=live_enabled,
            from_number_configured=from_configured,
        )

    def ensure_available(self) -> None:
        st = self.status()
        if not st.enabled:
            raise PhoneCallConfigError("Phone calls are disabled")
        if not st.live_chat_enabled:
            raise PhoneCallConfigError("Live chat is disabled")
        if not st.twilio_configured:
            raise PhoneCallConfigError("Twilio credentials are not configured")
        if not st.from_number_configured:
            raise PhoneCallConfigError("Twilio from number is not configured")
        if not st.media_stream_configured:
            raise PhoneCallConfigError("Twilio media stream WSS URL is not configured")

    def normalize_phone_number(self, raw: str) -> str:
        s = (raw or "").strip()
        if s.startswith("+"):
            candidate = "+" + "".join(_PHONE_DIGITS_RE.findall(s))
        else:
            digits = "".join(_PHONE_DIGITS_RE.findall(s))
            country = (self.config.default_country_code or "+1").strip()
            candidate = f"{country}{digits}"
        if not is_e164_phone_number(candidate):
            raise ValueError("phone_number must be a valid E.164 phone number")
        return candidate

    @staticmethod
    def mask_phone_number(e164: str) -> str:
        if len(e164) <= 5:
            return "***"
        return f"{e164[:2]}***{e164[-4:]}"

    def phone_number_hmac(self, e164: str) -> str:
        return hmac.new(
            self.security.secret_key.encode("utf-8"),
            e164.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    async def bind_caller_number(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        agent_id: str,
        normalized_phone_number: str,
    ) -> None:
        phone_hash = self.phone_number_hmac(normalized_phone_number)
        masked = self.mask_phone_number(normalized_phone_number)
        result = await db.execute(
            select(PhoneCallCallerBinding).where(
                PhoneCallCallerBinding.phone_number_hmac == phone_hash
            )
        )
        binding = result.scalar_one_or_none()
        if binding is None:
            binding = PhoneCallCallerBinding(
                user_id=user_id,
                phone_number_hmac=phone_hash,
                phone_number_masked=masked,
                last_agent_id=agent_id,
            )
            db.add(binding)
        else:
            binding.user_id = user_id
            binding.phone_number_masked = masked
            binding.last_agent_id = agent_id
        await db.commit()

    async def lookup_caller_user_id(
        self, db: AsyncSession, *, normalized_phone_number: str
    ) -> str | None:
        phone_hash = self.phone_number_hmac(normalized_phone_number)
        result = await db.execute(
            select(PhoneCallCallerBinding.user_id).where(
                PhoneCallCallerBinding.phone_number_hmac == phone_hash
            )
        )
        return result.scalar_one_or_none()

    def create_media_token(
        self,
        *,
        user_id: str,
        agent_id: str,
        direction: str,
        chat_id: str | None = None,
        call_sid: str | None = None,
        speech_language_code: str | None = None,
        response_language_name: str | None = None,
    ) -> str:
        exp_dt = datetime.now(timezone.utc) + timedelta(
            seconds=int(self.config.media_stream_token_ttl_seconds)
        )
        payload = {
            "sub": user_id,
            "agent_id": agent_id,
            "chat_id": chat_id,
            "direction": direction,
            "jti": str(uuid.uuid4()),
            "call_sid": call_sid,
            "speech_language_code": speech_language_code,
            "response_language_name": response_language_name,
            "exp": int(exp_dt.timestamp()),
        }
        return jwt.encode(
            payload,
            self.security.secret_key,
            algorithm=self.security.algorithm,
        )

    def verify_media_token(self, token: str) -> PhoneCallMediaTokenPayload:
        try:
            payload = jwt.decode(
                token,
                self.security.secret_key,
                algorithms=[self.security.algorithm],
            )
        except JWTError as exc:
            raise ValueError("Invalid phone-call media token") from exc
        return PhoneCallMediaTokenPayload.model_validate(payload)

    def media_stream_url(self, token: str) -> str:
        return (
            f"{self.media_stream_base_url}/api/v1/phone-calls/twilio-media?"
            + urlencode({"token": token})
        )

    def build_stream_twiml(self, *, token: str, intro_text: str) -> str:
        stream_url = xml_escape(self.media_stream_url(token), {'"': "&quot;"})
        say = xml_escape(intro_text)
        return (
            "<Response>"
            f"<Say>{say}</Say>"
            "<Connect>"
            f'<Stream url="{stream_url}" />'
            "</Connect>"
            "</Response>"
        )

    @staticmethod
    def build_reject_twiml(message: str) -> str:
        return f"<Response><Say>{xml_escape(message)}</Say></Response>"

    def twilio_service(self) -> TwilioPhoneCallService:
        return TwilioPhoneCallService(
            account_sid=self.account_sid,
            auth_token=self.auth_token,
            from_number=self.from_number,
        )

    async def start_outbound_call(
        self,
        *,
        db: AsyncSession,
        current_user: User,
        agent_id: str,
        phone_number: str,
        subscription_svc: SubscriptionService,
        speech_language_code: str | None = None,
        response_language_name: str | None = None,
        reason: str = "",
        twilio_service: TwilioPhoneCallService | None = None,
    ) -> PhoneCallStartResponse:
        self.ensure_available()
        normalized = self.normalize_phone_number(phone_number)
        is_allowed, reject_reason, limit_info = await subscription_svc.check_live_chat_limit(
            db, current_user, agent_id
        )
        if not is_allowed:
            error_info = limit_info.get("error_info") or BusinessErrorCode.SUBSCRIPTION_REQUIRED
            raise PhoneCallLimitError(
                create_business_error_response(error_info).model_dump()
            )

        token = self.create_media_token(
            user_id=current_user.id,
            agent_id=agent_id,
            direction="outbound",
            speech_language_code=speech_language_code,
            response_language_name=response_language_name,
        )
        twiml = self.build_stream_twiml(
            token=token,
            intro_text="Connecting you to your Inty companion.",
        )
        svc = twilio_service or self.twilio_service()
        result: TwilioCallResult
        import asyncio

        result = await asyncio.to_thread(
            svc.create_call,
            to_number=normalized,
            twiml=twiml,
        )
        await self.bind_caller_number(
            db,
            user_id=current_user.id,
            agent_id=agent_id,
            normalized_phone_number=normalized,
        )
        logger.info(
            "phone_call outbound queued user_id={} agent_id={} to={} sid={} reason={}",
            current_user.id,
            agent_id,
            self.mask_phone_number(normalized),
            result.sid,
            reason[:80],
        )
        return PhoneCallStartResponse(
            call_sid=result.sid,
            status=result.status,
            agent_id=agent_id,
            to_number_masked=self.mask_phone_number(normalized),
        )

    def agent_id_for_inbound_number(self, to_number: str) -> str | None:
        try:
            normalized = self.normalize_phone_number(to_number)
        except ValueError:
            normalized = to_number.strip()
        mapping = self.config.inbound_number_agent_map or {}
        return mapping.get(normalized) or (self.config.default_inbound_agent_id or None)

    async def build_inbound_twiml(
        self,
        *,
        db: AsyncSession,
        inbound: PhoneCallInboundWebhookRequest,
    ) -> str:
        if not self.config.enabled:
            return self.build_reject_twiml("Phone calls are currently disabled.")
        if not self.media_stream_base_url:
            return self.build_reject_twiml("Phone calls are not fully configured.")
        agent_id = self.agent_id_for_inbound_number(inbound.to_number)
        if not agent_id:
            return self.build_reject_twiml("This Inty phone number is not assigned yet.")
        try:
            caller = self.normalize_phone_number(inbound.from_number)
        except ValueError:
            return self.build_reject_twiml("We could not recognize your caller number.")
        user_id = await self.lookup_caller_user_id(
            db, normalized_phone_number=caller
        )
        if not user_id:
            return self.build_reject_twiml(
                "Please open the app and ask your Inty to call you once before calling this number."
            )
        token = self.create_media_token(
            user_id=user_id,
            agent_id=agent_id,
            direction="inbound",
            call_sid=inbound.call_sid,
        )
        return self.build_stream_twiml(
            token=token,
            intro_text="Connecting you to your Inty companion.",
        )

    def extract_call_me_at_number(self, text: str) -> str | None:
        match = _CALL_ME_AT_RE.search(text or "")
        if not match:
            return None
        return match.group("number")


phone_call_service = PhoneCallService()
