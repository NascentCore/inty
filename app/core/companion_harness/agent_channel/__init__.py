"""Agent-channel scope types for multi-medium companion endpoints (parallel to legacy chat scope).

``AgentScope`` and synthetic MemoryStore keys live in ``agent_channel.scope``;
service-layer bind/resolve/runtime is in ``app.services.agentic_channel``.

TODO(rename-channel-to-gateway): Rename "Channel" to "Gateway" — these layers are gateways to
human channels (weixin/wechat, telegram, sms-phone-number, etc.).
"""
