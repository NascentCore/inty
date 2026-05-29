"""Ops Weixin channel: Hermes transport + in-process companion presence.

iLink: QR poll token expires via ``status=expired``; bridge ``bot_token`` ends on
``errcode=-14`` (not a 14-minute QR TTL). See ``ilink_qr_client``, ``weixin_qr_flow``.

``WeixinQrFlow`` polls iLink QR login for ``/wechat-demo`` sessions via ``ilink_qr_client``.
``WeixinTransport`` owns Hermes ``WeixinAdapter`` (iLink long-poll).
``WeixinChannelSession`` binds one companion ``(user, agent)`` to one Weixin DM peer
via ``WeixinInprocessPresence`` (no ``/api/v1/chat/ws`` loopback). iLink cannot
report WeChat user presence (open app / open DM); see ``ilink_qr_client``, ``transport``.

Outbound: Inty gives Hermes one assistant string. Hermes may split that string into several WeChat bubbles when sending.
Depending on heuristics (message length, line breaks);
and ``weixin_channel.split_multiline_messages`` force splitting text into multiple lines,
each of the lines becomes a separate WeChat bubble.
See ``transport`` for the detailed sending model.

``chat_ws_wire`` holds shared ``/api/v1/chat/ws`` response parsing helpers.

Upstream parity: ``ilink_qr_client`` TODO(weixin-upstream-parity); adapter
product-layer NOTE in ``transport``.
"""
