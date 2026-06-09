"""Production iMate companion kernel package.

This package contains the stateful agentic companion backend used by iMate WebSocket chat:
session management, MemoryStore-backed workspace documents, prompt assembly, turn execution,
memory updates, async tool background work, and connection-level
WebSocket coordination.

TODO(companion-multimodal-user-turn): Phase 1 — user chat accepts images via
``CompanionUserTurnInput`` (see ``user_turn_input.py``) and ``run_user_chat``;
Weixin/WS are channel adapters (Phase 2 for Weixin).
"""
