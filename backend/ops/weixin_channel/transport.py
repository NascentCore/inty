"""Hermes ``WeixinAdapter`` transport for Ops Weixin channel.

NOTE(weixin-adapter-product-layer): ``WeixinAdapter`` encapsulates iLink-facing
product behaviors beyond raw HTTP: inbound message deduplication, Markdown and
~4000-character chunking, typing indicators, per-peer ``context_token`` persistence,
AES-128-ECB CDN encrypt/decrypt for media, and SSRF validation on outbound media
URLs. This Ops bridge currently surfaces text DMs only; dropping Hermes for a
custom iLink client requires an explicit decision per behavior so Inty UX stays
intentional—not accidentally weaker or stricter than today.

Hermes Weixin user guide — media (plain language, aligned with upstream docs):

Transport mental model — WeChat/iLink does not give a permanent public raw file
URL like a static image host. Media goes through their CDN with per-message key
material. Inbound: download ciphertext from CDN using encrypted query params,
decrypt with the per-file key embedded in the message payload → real bytes for
the agent. Outbound: generate a random AES key, encrypt file bytes (AES-128-ECB
+ PKCS#7 per Hermes docs), call ``getuploadurl``, PUT ciphertext to CDN, then
send the chat message carrying the CDN reference. ``AES-128-ECB`` is only the
cipher name; the point is "bytes on the CDN hop are encrypted, not a naked GET."

SSRF (separate concern): when the adapter downloads media from a URL supplied in
message content, it rejects private/internal targets so a peer cannot trick the
gateway into probing ``localhost`` or RFC1918 addresses.

NOTE(weixin-voice-hermes): Voice readability on the companion path is decided in
Hermes before Inty sees ``MessageEvent``: ``_extract_text`` prefers
``voice_item.text``; ``_download_voice`` runs only when that field is empty.
Our bridge never re-fetches or transcribes audio—only forwards Hermes ``text`` or
answers with a fallback when Hermes surfaced ``audio/silk`` without text.

Inbound — what ``WeixinAdapter`` does with user attachments (before our bridge
sees ``MessageEvent.text`` only for the text path we wire today):

- Images — fetch from CDN, decrypt, cache locally as JPEG for downstream use.
- Video — decrypt from CDN, cache as MP4.
- Files — decrypt, cache; original filename preserved when the payload allows.
- Voice — if WeChat provides a text transcription, the adapter prefers that text
  and our bridge forwards it to the companion like any text DM; otherwise
  download/decrypt audio and cache as SILK, and the bridge replies with a
  voice-specific fallback (no Inty SILK/ASR yet).
  TODO(weixin-voice-asr): Decode Hermes-cached SILK from ``media_paths`` and run
  batch ASR (e.g. Gemini) so untranscribed voice DMs reach the companion without
  relying on WeChat ``voice_item.text``.
- Quoted / reply-to messages — media referenced inside quotes may be extracted so
  the agent sees what the user is replying to.

WeChat user presence — **not available** on the existing iLink API path: long-poll
``getupdates`` delivers user/bot DMs (text/media) only. Hermes ``WeixinAdapter`` drops
updates with no text and no media, so "opened chat but sent nothing" is invisible.
Outbound ``sendtyping`` is bot→user only; it does not surface user online or in-thread
state. Product proxies: inbound DM timestamp (see ``WeixinChannelBinding.last_peer_seen_at``).

Outbound — Hermes adapter entry points (this module only calls ``send`` today):

- ``send`` — text; Markdown is preserved when the WeChat client + iLink path can
  render it.
- ``send_image`` / ``send_image_file`` — native image bubble: encrypt, CDN upload,
  send reference.
- ``send_document`` — file attachment: same encrypted CDN upload flow.
- ``send_video`` — video message: same encrypted CDN upload flow.
Long-poll/send use ``weixin_token`` (iLink ``bot_token``). When iLink session ends,
``getupdates`` / ``sendmessage`` return ``errcode=-14`` (session expired; **not**
“14 minutes”). ``on_ilink_session_expired`` disconnects Hermes, fails the demo session,
and deletes the Postgres bridge row (no 10-minute poll retry).

TODO(wechat-demo-ilink-session-expired-user-notify): After ``-14`` the ``bot_token`` cannot
send WeChat DMs, so **cannot** ask the chatter to re-scan QR inside WeChat chat; re-auth is
QR on Ops ``/wechat-demo``. Optional: restore-time ``getupdates`` probe before connect;
one-shot DM to ``last_peer_id`` with Ops re-login URL while token is still valid.

TODO(wechat-demo-ws-disconnect-hermes-wording): ``inbound_handler`` exceptions (e.g.
Inty WS ``ConnectionClosedError``) are caught by Hermes ``BasePlatformAdapter`` and
replied to WeChat with "use /reset"—Hermes CLI wording, not an Inty slash command.
"""

from __future__ import annotations

import asyncio
import contextvars
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from gateway.config import PlatformConfig
from gateway.platforms.base import MessageEvent
from gateway.platforms.weixin import WeixinAdapter
from loguru import logger

from backend.ops.weixin_channel.ilink_qr_client import (
    ILINK_SESSION_EXPIRED_ERRCODE,
    is_ilink_session_expired_runtime_error,
)

# Hermes ``WeixinAdapter._poll_loop`` logs session-expired on stdlib logging before sleeping;
# Ops rewrites the line and schedules bridge teardown (disconnect, no 10-minute retry).
_HERMES_WEIXIN_LOGGER = logging.getLogger("gateway.platforms.weixin")
_HERMES_SESSION_EXPIRED_PAUSE_SUBSTR = "Session expired; pausing for 10 minutes"
_weixin_transport_account_id: contextvars.ContextVar[str | None] = (
    contextvars.ContextVar(
        "weixin_transport_account_id",
        default=None,
    )
)
_weixin_hermes_log_filter_installed = False
_ilink_session_expired_handlers: dict[str, Callable[[], Awaitable[None]]] = {}
_ilink_session_expired_teardown_inflight: set[str] = set()

IlinkSessionExpiredHandler = Callable[[], Awaitable[None]]


def register_ilink_session_expired_handler(
    account_id: str,
    handler: IlinkSessionExpiredHandler,
) -> None:
    """Register teardown for one iLink ``account_id`` while ``WeixinTransport`` is up."""
    assert account_id != ""
    _ilink_session_expired_handlers[account_id] = handler


def unregister_ilink_session_expired_handler(account_id: str) -> None:
    """Drop handler when transport loop exits."""
    assert account_id != ""
    _ilink_session_expired_handlers.pop(account_id, None)


def schedule_ilink_session_expired_teardown(account_id: str) -> None:
    """Idempotently run registered handler (Hermes poll log or send failure)."""
    assert account_id != ""
    if account_id in _ilink_session_expired_teardown_inflight:
        return
    handler = _ilink_session_expired_handlers.get(account_id)
    if handler is None:
        return
    _ilink_session_expired_teardown_inflight.add(account_id)

    async def _run_teardown() -> None:
        try:
            await handler()
        finally:
            _ilink_session_expired_teardown_inflight.discard(account_id)

    asyncio.get_running_loop().create_task(
        _run_teardown(),
        name=f"weixin_ilink_expired_{account_id}",
    )


class WeixinIlinkSessionExpiredLogFilter(logging.Filter):
    """Rewrite Hermes getupdates ``errcode=-14`` log and schedule Ops bridge teardown."""

    def filter(self, record: logging.LogRecord) -> bool:
        if _HERMES_SESSION_EXPIRED_PAUSE_SUBSTR not in record.getMessage():
            return True
        account_id = _weixin_transport_account_id.get() or "unknown"
        record.msg = (
            "[weixin] iLink bot_token 已失效（errcode=%s）：WeChat demo 桥接 "
            "account_id=%s 无法收发消息；正在断开 Hermes 并清理 bridge——请在 Ops /wechat-demo "
            "重新扫码登录"
        )
        record.args = (ILINK_SESSION_EXPIRED_ERRCODE, account_id)
        if account_id != "unknown":
            schedule_ilink_session_expired_teardown(account_id)
        return True


def _ensure_weixin_hermes_session_expired_log_filter() -> None:
    global _weixin_hermes_log_filter_installed
    if _weixin_hermes_log_filter_installed:
        return
    _HERMES_WEIXIN_LOGGER.addFilter(WeixinIlinkSessionExpiredLogFilter())
    _weixin_hermes_log_filter_installed = True


@dataclass(frozen=True)
class WeixinCredential:
    """iLink bot credential after QR login."""

    account_id: str
    token: str
    base_url: str


@dataclass(frozen=True)
class WeixinInboundMessage:
    """Normalized inbound DM from Weixin iLink."""

    account_id: str
    peer_id: str
    # User-visible text; for voice DMs Hermes sets this from WeChat ``voice_item.text``
    # when present, else empty and ``media_paths`` / ``media_types`` carry SILK.
    text: str
    # Hermes WeixinAdapter local cache paths + MIME types (image-only DMs have empty text).
    # TODO(weixin-voice-asr): ``audio/silk`` paths here are the ASR input when WeChat
    # omits ``voice_item.text``; today only ``media_types`` gates the bridge fallback.
    media_paths: tuple[str, ...]
    media_types: tuple[str, ...]


WeixinInboundHandler = Callable[[WeixinInboundMessage], Awaitable[str]]


class WeixinTransport:
    """Long-poll Weixin DM transport; delegates replies to ``inbound_handler``."""

    def __init__(
        self,
        cred: WeixinCredential,
        inbound_handler: WeixinInboundHandler,
        on_ilink_session_expired: IlinkSessionExpiredHandler,
    ) -> None:
        assert cred.account_id != ""
        assert cred.token != ""
        assert cred.base_url != ""
        self._cred = cred
        self._inbound_handler = inbound_handler
        self._on_ilink_session_expired = on_ilink_session_expired
        self._adapter: WeixinAdapter | None = None
        self._stop = asyncio.Event()

    async def run_until_stopped(self) -> None:
        from app.core.config import global_config_loaded_from_config_yaml

        config = PlatformConfig(
            enabled=True,
            token=self._cred.token,
            extra={
                "account_id": self._cred.account_id,
                "base_url": self._cred.base_url,
                "dm_policy": "open",
                "group_policy": "disabled",
                "split_multiline_messages": (
                    global_config_loaded_from_config_yaml.weixin_channel.split_multiline_messages
                ),
            },
        )
        # TODO(weixin-adapter-parity): If we replace ``WeixinAdapter``, re-audit
        # Hermes Weixin docs/features (dedup, Markdown/chunking, typing, media CDN,
        # context_token store, retry/-14 handling) against Inty requirements.
        adapter = WeixinAdapter(config)

        async def handle_weixin_message(event: MessageEvent) -> str:
            # TODO(wechat-demo-ws-disconnect-hermes-wording): return-value path only; raises
            # from ``_inbound_handler`` become Hermes generic error DM to the peer.
            # Voice ``event.text`` is whatever Hermes extracted (WeChat transcription or
            # empty); we do not inspect raw iLink ``item_list`` here.
            peer_id = event.source.chat_id
            assert peer_id != ""
            inbound = WeixinInboundMessage(
                account_id=self._cred.account_id,
                peer_id=peer_id,
                text=event.text,
                media_paths=tuple(event.media_urls),
                media_types=tuple(event.media_types),
            )
            return await self._inbound_handler(inbound)

        adapter.set_message_handler(handle_weixin_message)
        self._adapter = adapter
        _ensure_weixin_hermes_session_expired_log_filter()
        register_ilink_session_expired_handler(
            self._cred.account_id,
            self._on_ilink_session_expired,
        )
        account_ctx = _weixin_transport_account_id.set(self._cred.account_id)
        try:
            await adapter.connect()
            while not self._stop.is_set():
                await asyncio.sleep(1)
        finally:
            unregister_ilink_session_expired_handler(self._cred.account_id)
            _weixin_transport_account_id.reset(account_ctx)

    async def send_text(self, peer_id: str, text: str) -> None:
        # Text-only path; image/file/video use adapter ``send_*`` (see module doc).
        assert peer_id != ""
        assert text != ""
        adapter = self._adapter
        assert adapter is not None
        try:
            result = await adapter.send(peer_id, text)
        except RuntimeError as exc:
            if is_ilink_session_expired_runtime_error(exc):
                schedule_ilink_session_expired_teardown(self._cred.account_id)
            raise
        if not getattr(result, "success", True):
            logger.warning(
                "weixin_transport send_text failed peer_id={} result={}",
                peer_id,
                result,
            )
            raise RuntimeError(f"Weixin send failed: {result}")

    async def stop(self) -> None:
        self._stop.set()
        if self._adapter is not None:
            await self._adapter.disconnect()
            self._adapter = None
