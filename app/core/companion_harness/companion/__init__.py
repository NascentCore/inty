"""Production iMate companion kernel package.

This package contains the stateful agentic companion backend used by iMate WebSocket chat:
session management, MemoryStore-backed workspace documents, prompt assembly, turn execution,
memory updates, async tool background work, and connection-level
WebSocket coordination.

TODO(companion-multimodal-user-turn): Phase 1 — user chat accepts images through a — #3293
future harness user-turn value object and ``run_user_chat``; Weixin/WS are channel
adapters (Phase 2 for Weixin).
https://github.com/NascentCore/inty/issues/3293

TODO(companion-package-reorg): Reorganize companion/ flat modules into companion_harness sub-packages (see issue body). — #3409
https://github.com/NascentCore/inty/issues/3409
"""
