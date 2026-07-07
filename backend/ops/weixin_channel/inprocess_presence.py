"""In-process companion presence for Weixin demo bridge (no ``/api/v1/chat/ws`` loopback).

Not WeChat user presence: iLink does not expose open-app or open-DM signals (see ``transport``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from app.api import deps
from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import ChannelKind
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services import agent_service
from app.services.agentic_channel.adapters.weixin import WeixinChannelAdapter
from app.services.agentic_channel.channel_runtime import (
    turn_channel_down,
    turn_channel_up,
)
from app.services.agentic_channel.presence import (
    ensure_presence,
    get_presence,
    stop_presence,
)
from backend.ops.weixin_channel.session import WeixinChannelBinding
from backend.ops.weixin_channel.weixin_downlink import WeixinDownlink

if TYPE_CHECKING:
    from backend.ops.weixin_channel.transport import WeixinTransport


async def _inty_user_from_binding(binding: WeixinChannelBinding) -> User | None:
    """JWT ``sub`` is the Inty user; ``binding.user_id`` is only the demo session UUID."""
    async with AsyncSessionLocal() as db:
        return await deps.get_user_from_token(binding.inty_jwt, db)


class WeixinInprocessPresence:
    """One Weixin binding: ``AgentChannelPresence`` + Hermes text downlink."""

    def __init__(self, binding: WeixinChannelBinding) -> None:
        assert binding is not None
        self._binding = binding
        self._downlink: WeixinDownlink | None = None
        self._scope: AgentScope | None = None
        self._inty_user_id: str | None = None

    async def start(self, transport: WeixinTransport) -> None:
        """Register Weixin channel adapter and start scope queue serving."""
        assert transport is not None
        inty_user = await _inty_user_from_binding(self._binding)
        if inty_user is None:
            raise RuntimeError(
                "weixin inprocess presence: invalid or expired inty_jwt for demo bridge"
            )
        self._inty_user_id = str(inty_user.id)
        agent_id = self._binding.agent_id
        scope = AgentScope(user_id=self._inty_user_id, agent_id=agent_id)
        self._scope = scope
        self._downlink = WeixinDownlink(
            transport,
            lambda: self._binding.last_peer_id,
        )
        adapter = WeixinChannelAdapter(
            send_assistant_text=self._downlink.send_assistant_text,
        )
        await turn_channel_up(
            scope,
            ChannelKind.WECHAT_WEIXIN,
            adapter=adapter,
            reason="weixin_inprocess_start",
        )
        await ensure_presence(scope)

    async def stop(self) -> None:
        if self._scope is not None:
            await stop_presence(self._scope)
            await turn_channel_down(
                self._scope,
                ChannelKind.WECHAT_WEIXIN,
                reason="weixin_inprocess_stop",
            )
        self._scope = None
        self._inty_user_id = None

    async def handle_user_text(self, user_text: str) -> str:
        """Enqueue one user-chat turn and wake scope queue serving."""
        stripped = user_text.strip()
        assert stripped
        if self._scope is None or self._downlink is None:
            return "Weixin bridge is not started."
        if self._inty_user_id is None:
            inty_user = await _inty_user_from_binding(self._binding)
            if inty_user is None:
                return (
                    "This demo bridge could not verify your Inty token. "
                    "Stop the session and start again with a valid JWT."
                )
            self._inty_user_id = str(inty_user.id)

        try:
            async with AsyncSessionLocal() as db:
                inty_user = await deps.get_user_from_token(
                    self._binding.inty_jwt, db
                )
                if inty_user is None:
                    return (
                        "This demo bridge could not verify your Inty token. "
                        "Stop the session and start again with a valid JWT."
                    )
                agent_data = await agent_service.get_agent_for_chat(
                    db, self._binding.agent_id
                )
                if agent_data is None:
                    return "Companion not found for this bridge."

            presence = get_presence(self._scope)
            if presence is None:
                presence = await ensure_presence(self._scope)
            return await presence.handle_user_text(
                stripped,
                runtime_channel=ChannelKind.WECHAT_WEIXIN,
            )
        except Exception:
            logger.exception(
                "weixin inprocess user_chat failed user_id={} agent_id={}",
                self._inty_user_id,
                self._binding.agent_id,
            )
            return "Companion turn failed. Check Ops logs for weixin inprocess user_chat."
