"""In-process agentic companion: shared inner-tick + turn coordination across channel transports.

``Session`` owns sign-on, user turns, and the inner-tick worker; each
channel adapter implements :class:`~app.services.agentic_companion.downlink.ChannelDownlink`
to map :class:`~app.services.agentic_companion.downlink.Downlink` events to wire-specific
delivery (WebSocket frames, Weixin Hermes text, etc.).
"""
