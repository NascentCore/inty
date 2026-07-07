"""Shared runtime dependencies for one companion turn execution.

``CompanionTurnDeps`` is the single argument bundle for ``run_companion_*_turn``
track entry points and ``_run_companion_turn_core``. Production callers typically
build it via ``CompanionManager._build_turn_deps`` (session config + per-turn
overrides); tests and direct harness callers construct it explicitly.

Field provenance:

- **Session-scoped** (from ``CompanionSession`` / ``CompanionConfig``): ``store``,
  ``llm_client``, ``transcript_compaction``, ``transcript_llm_window_max_messages``,
  ``repository_only_store_text``, ``langsmith_parent_run_enabled``, ``tool_bg_idle_event``.
- **Per-turn** (from the wire / API layer each invocation): ``runtime_context``,
  ``preset_user_msg_uuid``.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.transcript_compaction import (
    CompactionConfig as TranscriptCompactionConfig,
)

from app.core.llms.client import LlmClient
from .langsmith_turn_slice import CompanionTurnLangsmithSlice
from app.core.companion_harness.companion.runtime_channel import (
    TurnRuntimeContext,
)

if TYPE_CHECKING:
    from app.core.companion_harness.agentic_companion.output_queue import (
        OutputQueue,
    )
    from app.core.companion_harness.agentic_companion.types import (
        AgenticLoopInputBatch,
        UserMessageBatch,
    )


@dataclass(frozen=True)
class CompanionTurnDeps:
    """Immutable dependencies for one ``run_turn`` execution.

    Unpacked once at the top of ``_run_companion_turn_core``; inner helpers continue
    to receive primitive fields to keep the core diff small.

    Fields
    ------

    store
        ``MemoryStore`` for the paired user+companion scope. Loads and persists
        ``context.json``, MemoryDoc markdown (``IDENTITY.md``, ``SOUL.md``, …),
        ``transcript.jsonl`` / inner-tick transcripts, and tool write targets for
        this turn. Every turn reads prompt state from here and appends transcript
        rows when the round completes.

    llm_client
        ``LlmClient`` bound to this session's model routing (chat vs tool
        roles, API base, timeouts). All in-turn ``chat_completion`` calls and
        ``tool_background`` dispatch use this client; LangSmith parent runs also
        resolve model ids from it.

    transcript_compaction
        When non-``None``, older transcript dialogue may be folded into a structured
        system snapshot once the OpenAI message list exceeds a character budget
        (see ``transcript_compaction`` module). ``None`` disables compaction for
        this turn. Sourced from ``CompanionConfig.transcript_compaction``.

    transcript_llm_window_max_messages
        Cap on transcript rows loaded before compaction and prompt assembly. When
        ``None``, ``companion.models.TRANSCRIPT_WINDOW_MAX_MESSAGES`` applies.
        Only meaningful when ``transcript_compaction`` is configured.

    repository_only_store_text
        When ``True``, companion tools read/write textual MemoryStore documents
        only (no repository side paths for transcript/context markdown). Wired from
        ``CompanionConfig.repository_only_store_text`` and passed into tool
        execution (``execute_tool_call``, ``tool_background``).

    runtime_context
        Per-turn facts separate from MemoryDoc content: human-facing
        ``CompanionRuntimeChannel`` (app vs wechat/weixin) and optional
        ``ImplicitSignalBundle`` (sign-on greeting, proactive triggers). Drives
        output-format system slices, implicit sign-on user text substitution, and
        is forwarded into ``tool_background`` for channel-aware tool behavior.
        TODO(companion-channel-tools): channel tool executors read this + agent scope — #3362

    preset_user_msg_uuid
        When set, used as this turn's ``user_msg_uuid`` (correlates client message
        id, LangSmith runs, transcript rows, and REPL metadata). When ``None``,
        ``_run_companion_turn_core`` generates a fresh UUID. WebSocket handlers
        pass the client-supplied id so retries and traces align.

    langsmith_parent_run_enabled
        Tri-state LangSmith companion parent ``RunTree`` for this turn. ``None``:
        follow app-wide policy
        (``companion_turn_langsmith_parent_enabled_from_app_config``). ``True`` /
        ``False``: force on or off regardless of global config. Resolved in manager
        from ``CompanionConfig.langsmith_companion_parent_run_enabled`` when
        unset at session level.

    tool_bg_idle_event
        Session ``threading.Event`` cleared while ``tool_background`` owns the
        async tool loop and set when that thread finishes. ``_run_companion_turn_core``
        awaits this (with timeout) **before** loading transcript so the next turn
        sees tool summaries already appended. ``None`` skips the wait (tests). Production
        uses ``CompanionSession.tool_bg_idle``.

    agentic_output_queue
        Domain ``OutputQueue`` for queue-serving ``USER_CHAT`` / ``USER_CHAT_BOOTSTRAP``.
        When set with ``user_message_batch``, ``run_turn`` routes through
        ``AgenticLoop.run`` instead of dual-LLM or legacy bootstrap interim sink.

    user_message_batch
        Correlates ``OutputQueue`` appends with claimed input batch
        (``batch_id`` + ``message_ids``). Required when ``agentic_output_queue`` is set.
    """

    store: MemoryStore
    llm_client: LlmClient
    transcript_compaction: TranscriptCompactionConfig | None
    transcript_llm_window_max_messages: int | None
    repository_only_store_text: bool
    runtime_context: TurnRuntimeContext
    preset_user_msg_uuid: str | None
    langsmith_parent_run_enabled: bool | None
    tool_bg_idle_event: threading.Event | None
    agentic_output_queue: OutputQueue | None = None
    user_message_batch: UserMessageBatch | None = None
    input_batch: AgenticLoopInputBatch | None = None

    @property
    def langsmith_slice(self) -> CompanionTurnLangsmithSlice:
        """Turn-bound LangSmith channel tags shared by foreground and tool_background."""
        return CompanionTurnLangsmithSlice.from_runtime_context(
            self.runtime_context
        )
