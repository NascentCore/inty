"""Ops Weixin channel: Hermes transport + long-lived Inty ``/api/v1/chat/ws`` client.

iLink: QR poll token expires via ``status=expired``; bridge ``bot_token`` ends on
``errcode=-14`` (not a 14-minute QR TTL). See ``ilink_qr_client``, ``weixin_qr_flow``.

``WeixinQrFlow`` polls iLink QR login for ``/wechat-demo`` sessions via ``ilink_qr_client``.
``WeixinTransport`` owns Hermes ``WeixinAdapter`` (iLink long-poll).
``IntyWsChannelClient`` speaks the wire protocol via ``app.schemas.chat_websocket``.
``WeixinChannelSession`` binds one companion ``(user, agent)`` to one Weixin DM peer
for inbound replies and proactive downlink delivery.

Upstream parity: ``ilink_qr_client`` TODO(weixin-upstream-parity); adapter
product-layer NOTE in ``transport``.
TODO(wechat-demo-ws-disconnect-hermes-wording): Inty ``/api/v1/chat/ws`` close (often
uvicorn 1012 service restart) surfaces to WeChat as Hermes ``gateway/platforms/base.py``
"Sorry… ConnectionClosedError… Try again or use /reset". Inty has no ``/reset``; fix is
reconnect WS (Ops/Inty restart, wechat-demo stop/start, or bridge restore)—see
``inty_ws_client``, ``transport``, ``session``.
"""
