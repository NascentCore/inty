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

Inbound — what ``WeixinAdapter`` does with user attachments (before our bridge
sees ``MessageEvent.text`` only for the text path we wire today):

- Images — fetch from CDN, decrypt, cache locally as JPEG for downstream use.
- Video — decrypt from CDN, cache as MP4.
- Files — decrypt, cache; original filename preserved when the payload allows.
- Voice — if WeChat provides a text transcription, the adapter prefers that text;
  otherwise download/decrypt audio and cache as SILK for further handling.
- Quoted / reply-to messages — media referenced inside quotes may be extracted so
  the agent sees what the user is replying to.

Outbound — Hermes adapter entry points (this module only calls ``send`` today):

- ``send`` — text; Markdown is preserved when the WeChat client + iLink path can
  render it.
- ``send_image`` / ``send_image_file`` — native image bubble: encrypt, CDN upload,
  send reference.
- ``send_document`` — file attachment: same encrypted CDN upload flow.
- ``send_video`` — video message: same encrypted CDN upload flow.
Long-poll/send use ``weixin_token`` (iLink ``bot_token``). When iLink session ends,
``getupdates`` returns ``errcode=-14`` (session expired; **not** “14 minutes”).
Stop demo and re-scan QR.

TODO(wechat-demo-ws-disconnect-hermes-wording): ``inbound_handler`` exceptions (e.g.
Inty WS ``ConnectionClosedError``) are caught by Hermes ``BasePlatformAdapter`` and
replied to WeChat with "use /reset"—Hermes CLI wording, not an Inty slash command.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from gateway.config import PlatformConfig
from gateway.platforms.base import MessageEvent
from gateway.platforms.weixin import WeixinAdapter
from loguru import logger


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
    text: str
    # Hermes WeixinAdapter local cache paths + MIME types (image-only DMs have empty text).
    media_paths: tuple[str, ...]
    media_types: tuple[str, ...]


WeixinInboundHandler = Callable[[WeixinInboundMessage], Awaitable[str]]


class WeixinTransport:
    """Long-poll Weixin DM transport; delegates replies to ``inbound_handler``."""

    def __init__(
        self,
        cred: WeixinCredential,
        inbound_handler: WeixinInboundHandler,
    ) -> None:
        assert cred.account_id != ""
        assert cred.token != ""
        assert cred.base_url != ""
        self._cred = cred
        self._inbound_handler = inbound_handler
        self._adapter: WeixinAdapter | None = None
        self._stop = asyncio.Event()

    async def run_until_stopped(self) -> None:
        config = PlatformConfig(
            enabled=True,
            token=self._cred.token,
            extra={
                "account_id": self._cred.account_id,
                "base_url": self._cred.base_url,
                "dm_policy": "open",
                "group_policy": "disabled",
            },
        )
        # TODO(weixin-adapter-parity): If we replace ``WeixinAdapter``, re-audit
        # Hermes Weixin docs/features (dedup, Markdown/chunking, typing, media CDN,
        # context_token store, retry/-14 handling) against Inty requirements.
        adapter = WeixinAdapter(config)

        async def handle_weixin_message(event: MessageEvent) -> str:
            # TODO(wechat-demo-ws-disconnect-hermes-wording): return-value path only; raises
            # from ``_inbound_handler`` become Hermes generic error DM to the peer.
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
        await adapter.connect()
        while not self._stop.is_set():
            await asyncio.sleep(1)

    async def send_text(self, peer_id: str, text: str) -> None:
        # Text-only path; image/file/video use adapter ``send_*`` (see module doc).
        assert peer_id != ""
        assert text != ""
        adapter = self._adapter
        assert adapter is not None
        result = await adapter.send(peer_id, text)
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
