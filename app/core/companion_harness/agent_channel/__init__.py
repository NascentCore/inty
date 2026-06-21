"""Agent-channel scope types for multi-medium companion endpoints (parallel to legacy chat scope).

``AgentScope`` and synthetic MemoryStore keys live in ``agent_channel.scope``;
service-layer bind/resolve/runtime is in ``app.services.agentic_channel``.

TODO(rename-channel-to-gateway): Add ``agent_channel/gateway.py`` (``GatewayKind`` enum) and — #3548
``gateway_traits.py`` (harness traits as functions/registry). Adapters declare gateway kind;
they do not own the canonical enum.
"""
