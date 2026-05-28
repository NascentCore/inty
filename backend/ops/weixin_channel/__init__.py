"""Ops Weixin channel: Hermes transport + in-process companion presence.

iLink: QR poll token expires via ``status=expired``; bridge ``bot_token`` ends on
``errcode=-14`` (not a 14-minute QR TTL). See ``ilink_qr_client``, ``weixin_qr_flow``.

``WeixinQrFlow`` polls iLink QR login for ``/wechat-demo`` sessions via ``ilink_qr_client``.
``WeixinTransport`` owns Hermes ``WeixinAdapter`` (iLink long-poll).
``WeixinChannelSession`` binds one companion ``(user, agent)`` to one Weixin DM peer
via ``WeixinInprocessPresence`` (no ``/api/v1/chat/ws`` loopback). iLink cannot
report WeChat user presence (open app / open DM); see ``ilink_qr_client``, ``transport``.

``chat_ws_wire`` holds shared ``/api/v1/chat/ws`` response parsing helpers.

Upstream parity: ``ilink_qr_client`` TODO(weixin-upstream-parity); adapter
product-layer NOTE in ``transport``.
"""
