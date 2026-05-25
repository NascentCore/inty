"""Ops Weixin channel: Hermes transport + long-lived Inty ``/api/v1/chat/ws`` client.

``WeixinQrFlow`` polls iLink QR login for ``/wechat-demo`` sessions via ``ilink_qr_client``.
``WeixinTransport`` owns Hermes ``WeixinAdapter`` (iLink long-poll).
``IntyWsChannelClient`` speaks the wire protocol via ``app.schemas.chat_websocket``.
``WeixinChannelSession`` binds one companion ``(user, agent)`` to one Weixin DM peer
for inbound replies and proactive downlink delivery.

Upstream parity: ``ilink_qr_client`` TODO(weixin-upstream-parity); adapter
product-layer NOTE in ``transport``.
"""
