"""In-process companion presence: shared inner-tick + turn coordination across channel transports.

``CompanionPresenceSession`` owns sign-on, user turns, and the inner-tick worker; each
``ChannelTransport`` implements :class:`~app.services.companion_presence.downlink.CompanionChannelDownlink`
to map :class:`~app.services.companion_presence.downlink.CompanionDownlink` events to wire-specific
delivery (WebSocket frames, Weixin Hermes text, etc.).
"""
