"""Agent-channel scope types for multi-medium companion endpoints (parallel to legacy chat scope).

``AgentScope`` and synthetic MemoryStore keys live in ``agent_channel.scope``;
service-layer bind/resolve/runtime is in ``app.services.agentic_channel``.

``ChannelKind`` and ``TurnRuntimeContext`` live in
``app.core.companion_harness.companion.runtime_channel`` (#3661). Adapters declare
``channel``; they do not own the canonical enum.
"""
