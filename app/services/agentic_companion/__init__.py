"""In-process agentic companion: glue between companion harness, channels, and chat WS.

``Session`` owns sign-on, user turns, and the inner-tick worker; each
channel adapter implements :class:`~app.services.agentic_companion.downlink.ChannelDownlink`
to map :class:`~app.services.agentic_companion.downlink.Downlink` events to wire-specific
delivery (WebSocket frames, Weixin Hermes text, etc.).

Inner-tick kernel due checks and ``run_inner_tick_*`` turns live in
``app.core.companion_harness.runtime.inner_tick_fire``; this package wires them to
``chat_history``, outbound queues, and ``agentic_channel`` adapters.

:class:`~app.services.agentic_companion.presence_registry.CompanionPresenceRegistry`
enforces one live WebSocket presence per ``(user_id, agent_id)`` at ``user_signed_on``.
"""
