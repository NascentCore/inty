"""Transport adapters: one ``CompanionRuntimeChannel`` → outbound delivery + turn hooks.

``ChannelAdapter`` protocol lives in ``adapters.base``:

- ``channel`` — which ``CompanionRuntimeChannel`` this adapter serves.
- ``as_downlink()`` — ``ChannelDownlink`` used while channel is ACTIVE (user reply,
  proactive, scheduled, maintenance text).
- ``on_turn_up`` / ``on_turn_down`` — lifecycle when ``channel_runtime.turn_channel_*``
  marks channel ACTIVE or INACTIVE for an ``AgentScope``.

``channel_runtime`` holds per-scope registries; exactly one channel ACTIVE at a time.
Inbound routing + 1:1 bonding use ``endpoints`` rows
(``channel_address`` = opaque routing key, ``channel_user_id`` = channel-side human id).

Implementations:

- ``telegram.TelegramChannelAdapter`` — ``sendMessage(chat_id=channel_address)``.
- ``weixin.WeixinChannelAdapterStub`` — no-op downlink; docs
  ``channel_address=peer_id``, ``channel_user_id=wxid`` (production bridge unchanged).

TODO(!3488): ``app_ws.AppWsChannelAdapter`` — WS completion materialization for OutputQueue delivery.
"""
