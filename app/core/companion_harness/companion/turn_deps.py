"""Shared runtime dependencies for one companion turn execution.

Generated entirely by Cursor agent for CompanionTurnDeps refactor.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.transcript_compaction import (
    CompactionConfig as TranscriptCompactionConfig,
)

from .llm_client import CompanionLLMClient
from .runtime_channel import TurnRuntimeContext
from .turn_routes import BackgroundToolEventSink, BootstrapInterimOutputSink


@dataclass(frozen=True)
class CompanionTurnDeps:
    """Immutable bundle passed into track entry points and ``_run_companion_turn_core``."""

    store: MemoryStore
    llm_client: CompanionLLMClient
    transcript_compaction: TranscriptCompactionConfig | None
    transcript_llm_window_max_messages: int | None
    repository_only_store_text: bool
    memory_bootstrap_type: str
    runtime_context: TurnRuntimeContext
    background_output_sink: BackgroundToolEventSink | None
    preset_user_msg_uuid: str | None
    langsmith_parent_run_enabled: bool | None
    tool_bg_idle_event: threading.Event | None
    bootstrap_interim_output_sink: BootstrapInterimOutputSink | None
