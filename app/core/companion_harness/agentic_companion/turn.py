"""Agent-channel user turns driven by the companion harness, persisted to MemoryStore only.

The turn seam between an external human channel (Telegram, Weixin, SMS, …) and the
companion harness for one user bound to one Inty agent. Sessions are addressed by a
synthetic MemoryStore key derived from the scope, never a legacy ``chats`` row, so all
state lives in MemoryStore with no ``chat_history`` writes. Sessions are resolved through
the companion manager and must already carry their minimal seed; an unseeded store is a
programming error, not something repaired mid-turn.

Usage scenarios:

- Provisioning / WS bootstrap: ensure a seeded session exists before any turn runs.
- Inbound user turn: execute one user message; caller already holds the scope turn lock
  (asserted, not acquired). Injects the one-time session-system message for interactive
  bootstrap, backfills client time from MemoryStore, then delegates to the manager.
"""

from __future__ import annotations

import json
import time
import uuid

from loguru import logger

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.output_queue import (
    OutputQueue,
)
from app.core.companion_harness.agentic_companion.types import UserMessageBatch
from app.core.companion_harness.companion.manager import CompanionSession
from app.core.companion_harness.companion.manager_factory import (
    DEFAULT_COMPANION_WS_SESSION_SYSTEM_TEXT,
    companion_manager_for_resolved_model,
    companion_runtime_config_fingerprint,
    companion_tool_model_api_id,
)
from app.core.companion_harness.companion.models import load_context_meta
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.scope_turn_lock import (
    assert_scope_turn_lock_held_by_current_task,
)
from app.core.companion_harness.companion.turn_routes import (
    BackgroundToolEventSink,
)
from app.core.companion_harness.companion.utc import utc_iso_ts
from app.core.companion_harness.memory.client_time_from_memory_store import (
    client_time_from_memory_store,
)
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)
from app.core.config import global_config_loaded_from_config_yaml
from app.utils.config import CompanionMemoryBootstrapType
from app.utils.models_catalog import GenAIModel


def _mark_agent_channel_session_system_written(
    session: CompanionSession,
) -> None:
    # TODO(memdoc-path-constants): context.json → DEFAULT_MEMORY_STORE_SCOPE_PATHS.context_json. #3413
    rel = "context.json"
    raw = session.store.read_document_if_exists(rel)
    if raw is None or not str(raw).strip():
        return
    data = json.loads(raw)
    if not isinstance(data, dict):
        return
    data["agent_channel_session_system_written"] = True
    session.store.write_document(
        rel, json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    )


async def _maybe_append_agent_channel_session_system(
    *,
    session: CompanionSession,
) -> None:
    if (
        session.config.memory_bootstrap_type
        != CompanionMemoryBootstrapType.USER_INTERACTIVE.value
    ):
        return
    meta = load_context_meta(store=session.store)
    if meta.workspace_bootstrap_user_interactive_completed:
        return
    if meta.companion_ws_session_system_written:
        return
    ctx_raw = session.store.read_document_if_exists("context.json")
    if ctx_raw:
        ctx_data = json.loads(ctx_raw)
        if isinstance(ctx_data, dict) and ctx_data.get(
            "agent_channel_session_system_written"
        ):
            return

    harness = global_config_loaded_from_config_yaml.agent.companion_harness
    text = (harness.ws.session_system_text or "").strip() or (
        DEFAULT_COMPANION_WS_SESSION_SYSTEM_TEXT
    )
    trace_id = str(uuid.uuid4())
    msg_uuid = str(uuid.uuid4())
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    session.store.append_jsonl_record(
        paths.transcript,
        {
            "role": "system",
            "content": text,
            "ts": utc_iso_ts(),
            "uuid": msg_uuid,
            "trace_id": trace_id,
            "source": "agent_channel",
            "agent_channel_session_system": True,
        },
    )
    _mark_agent_channel_session_system_written(session)
    logger.info(
        "agent_channel_session_system_written user={} agent={} chat={}",
        session.user_id,
        session.companion_id,
        session.chat_id,
    )


def manager_and_session_for_scope(
    scope: AgentScope,
    *,
    resolved_chat_model: GenAIModel,
) -> tuple[object, CompanionSession]:
    chat_api_id = resolved_chat_model.id_on_provider
    tool_api_id = companion_tool_model_api_id(chat_api_id)
    manager = companion_manager_for_resolved_model(
        chat_api_id,
        tool_api_id,
        companion_runtime_config_fingerprint(),
    )
    synthetic_chat_id = scope.memory_store_chat_id()
    session = manager.get_or_create_session(
        scope.user_id,
        scope.agent_id,
        synthetic_chat_id,
    )
    if not session.is_initialized:
        if (
            session.config.memory_bootstrap_type
            == CompanionMemoryBootstrapType.USER_INTERACTIVE.value
        ):
            raise RuntimeError(
                "Companion MemoryStore not seeded (interactive bootstrap requires minimal documents in store)"
            )
        raise RuntimeError(
            "Companion MemoryStore not initialized (expected minimal seed at session create)"
        )
    return manager, session


async def run_agent_turn(
    *,
    scope: AgentScope,
    user_text: str,
    resolved_chat_model: GenAIModel,
    runtime_channel: CompanionRuntimeChannel,
    background_output_sink: BackgroundToolEventSink | None,
    preset_user_msg_uuid: str | None,
    implicit_signal_bundle,
    agentic_output_queue: OutputQueue | None = None,
    user_message_batch: UserMessageBatch | None = None,
) -> object:
    """Run one user-chat turn without ``chat_history`` writes.

    Caller must already hold ``session.turn_lock`` for ``scope``; this function does not acquire it.
    """
    assert user_text.strip() != ""
    t0 = time.perf_counter()
    manager, session = manager_and_session_for_scope(
        scope, resolved_chat_model=resolved_chat_model
    )
    assert_scope_turn_lock_held_by_current_task(session.scope)
    await _maybe_append_agent_channel_session_system(session=session)
    bundle = implicit_signal_bundle
    # TODO(#3411): Manual E2E — after USER.md 时区 persisted, verify enrichment + LangSmith time slice.
    if bundle.client_time is None:
        client_time = client_time_from_memory_store(session.store)
        if client_time is not None:
            bundle = bundle.model_copy(update={"client_time": client_time})
    out = await manager.run_user_chat_turn(
        session,
        user_text,
        background_output_sink=background_output_sink,
        preset_user_msg_uuid=preset_user_msg_uuid,
        runtime_context=TurnRuntimeContext(
            channel=runtime_channel,
            implicit_signal_bundle=bundle,
        ),
        agentic_output_queue=agentic_output_queue,
        user_message_batch=user_message_batch,
    )
    logger.info(
        "agent_channel turn finished scope={} channel={} total_ms={:.0f}",
        scope.registry_key(),
        runtime_channel.value,
        (time.perf_counter() - t0) * 1000.0,
    )
    return out
