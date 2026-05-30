"""Route selected chat traffic through the agentic companion kernel (same as inty v2 REPL).

Companion concurrency (scope vs presence vs cluster): documented on
``app.services.agentic_companion.session.Coordinator`` and ``companion.manager.CompanionActivityGate``.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import uuid
from functools import lru_cache
from typing import Any

from loguru import logger

from app.core.companion_harness.companion.runtime_events import (
    append_runtime_event,
)
from app.core.companion_harness.companion.dreaming import (
    dreaming_due,
    dreaming_race_guard_matches,
    dreaming_state_from_candidate,
    save_dreaming_state,
)
from app.core.companion_harness.companion.llm_client import CompanionLLMConfig
from app.core.companion_harness.companion.turn_routes import (
    BackgroundToolEventSink,
    BootstrapInterimOutputSink,
)
from app.core.companion_harness.companion.manager import (
    CompanionConfig,
    CompanionManager,
    CompanionSession,
)
from app.core.companion_harness.memory.memory_registry import (
    MEMORY_STORE_REGISTRY_REQUIRES_DSN,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_pipeline import (
    memory_update_after_dreaming,
)
from app.core.companion_harness.companion.implicit_signal_messages import (
    implicit_user_signed_on_chat_turn,
)
from app.core.companion_harness.companion.models import (
    CompanionIdentity,
    CompanionTurnResult,
    InnerTickActivity,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from app.core.companion_harness.memory.transcript_compaction import (
    CompactionConfig as TranscriptCompactionConfig,
)
from app.core.config import global_config_loaded_from_config_yaml
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.utils.config import CompanionMemoryBootstrapType
from app.utils.models_catalog import GenAIModel, resolve_chat_text_model

DEFAULT_COMPANION_WS_SESSION_SYSTEM_TEXT = (
    "（会话入线，内部指令）用户已进入本聊天。请在本轮及之后延续自然陪伴：可先简短问候，"
    "并温和邀请对方说说此刻状态或想聊的事；不要提及系统、连接、初始化、工具名。"
)


def _companion_tool_call_model_yaml(agent: object) -> str:
    """Stripped ``AgentConfig.companion_tool_call_model``; empty means use chat model id."""
    return (getattr(agent, "companion_tool_call_model", "") or "").strip()


def _companion_tool_model_api_id(chat_model_api_id: str) -> str:
    """OpenRouter-style id for tool rounds; defaults to chat model when YAML override is empty."""
    cfg = global_config_loaded_from_config_yaml
    raw = _companion_tool_call_model_yaml(cfg.agent)
    if not raw:
        return chat_model_api_id
    return resolve_chat_text_model(raw).id_on_provider


def companion_memory_store_if_ready(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    resolved_chat_model: GenAIModel,
) -> MemoryStore | None:
    """Return the session MemoryStore when minimal companion documents are initialized."""
    chat_api_id = resolved_chat_model.id_on_provider
    tool_api_id = _companion_tool_model_api_id(chat_api_id)
    manager = _companion_manager_for_resolved_model(
        chat_api_id,
        tool_api_id,
        _companion_runtime_config_fingerprint(),
    )
    session = manager.get_or_create_session(user_id, agent_id, str(chat_id))
    if not session.is_initialized:
        return None
    return session.store


def companion_session_dreaming_active(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    resolved_chat_model: GenAIModel,
) -> bool:
    """Return whether this companion scope is in exclusive dreaming (``activity_gate``).

    Scope-level flag — true for any presence while ``run_companion_dreaming_for_api`` or
    future inner-tick ``DREAMING`` holds the gate. Does not reflect ``turn_lock`` state.
    """
    # TODO(obscure-abstraction): This is a high-level API, but it uses primitive data to retrieve
    # high-level abstraction classes. This violates layering principle.
    # This function is forced to exist because the caller does not properly setup high-level
    # abstraction classes.
    assert user_id
    assert agent_id
    chat_api_id = resolved_chat_model.id_on_provider
    tool_api_id = _companion_tool_model_api_id(chat_api_id)
    manager = _companion_manager_for_resolved_model(
        chat_api_id,
        tool_api_id,
        _companion_runtime_config_fingerprint(),
    )
    session = manager.get_or_create_session(user_id, agent_id, str(chat_id))
    return session.activity_gate.dreaming_active()


def companion_session_tool_bg_idle_event(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    resolved_chat_model: GenAIModel,
) -> threading.Event:
    """Return ``CompanionSession.tool_bg_idle`` for WebSocket inner-tick overlap checks.

    TODO(tool-bg-idle-starves-user-chat): Hung maintenance ``tool_background`` clears this event;
    the next user or proactive turn blocks in ``run_turn`` while holding ``turn_lock``.
    https://github.com/NascentCore/inty/issues/3123
    """
    chat_api_id = resolved_chat_model.id_on_provider
    tool_api_id = _companion_tool_model_api_id(chat_api_id)
    manager = _companion_manager_for_resolved_model(
        chat_api_id,
        tool_api_id,
        _companion_runtime_config_fingerprint(),
    )
    session = manager.get_or_create_session(user_id, agent_id, str(chat_id))
    return session.tool_bg_idle


def run_companion_dreaming_for_api(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    resolved_chat_model: GenAIModel,
    dreaming_idle_seconds: int,
) -> bool:
    """Run one sleeping-state dreaming batch for a ready companion scope.

    Uses ``CompanionActivityGate.enter_dreaming`` (scope level), not ``Coordinator.turn_lock``.
    Typically invoked from ``CompanionDreamingScheduler`` without an open WebSocket.
    Awake turns on any wire block in ``CompanionManager._awake_activity`` until exit.
    """
    chat_api_id = resolved_chat_model.id_on_provider
    tool_api_id = _companion_tool_model_api_id(chat_api_id)
    manager = _companion_manager_for_resolved_model(
        chat_api_id,
        tool_api_id,
        _companion_runtime_config_fingerprint(),
    )
    session = manager.get_or_create_session(user_id, agent_id, str(chat_id))
    if not session.is_initialized:
        return False
    from datetime import datetime, timezone

    candidate = dreaming_due(
        session.store,
        now=datetime.now(timezone.utc),
        dreaming_idle_seconds=dreaming_idle_seconds,
    )
    if candidate is None:
        return False

    session.activity_gate.enter_dreaming()
    try:
        candidate = dreaming_due(
            session.store,
            now=datetime.now(timezone.utc),
            dreaming_idle_seconds=dreaming_idle_seconds,
        )
        if candidate is None:
            return False

        def _complete_fn(messages: list[dict[str, Any]], role: str) -> str:
            return session.llm_client.complete_text(messages, model_role=role)

        memory_update_after_dreaming(
            session.store,
            candidate.rows,
            _complete_fn,
            tool_bg_idle_event=session.tool_bg_idle,
        )
        if not dreaming_race_guard_matches(session.store, candidate):
            logger.info(
                "companion_dreaming checkpoint_skipped_race user={} agent={} chat={}",
                user_id,
                agent_id,
                chat_id,
            )
            return False
        state = dreaming_state_from_candidate(
            candidate, processed_at=datetime.now(timezone.utc)
        )
        save_dreaming_state(session.store, state)
        logger.info(
            "companion_dreaming checkpoint_saved user={} agent={} chat={} rows={}",
            user_id,
            agent_id,
            chat_id,
            len(candidate.rows),
        )
        return True
    finally:
        session.activity_gate.exit_dreaming()


def append_companion_ws_runtime_event(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    resolved_chat_model: GenAIModel,
    record: dict[str, Any],
) -> None:
    """Append one WS control-frame audit record to ``.companion_runtime_events.jsonl``."""
    chat_api_id = resolved_chat_model.id_on_provider
    tool_api_id = _companion_tool_model_api_id(chat_api_id)
    manager = _companion_manager_for_resolved_model(
        chat_api_id,
        tool_api_id,
        _companion_runtime_config_fingerprint(),
    )
    session = manager.get_or_create_session(user_id, agent_id, str(chat_id))
    append_runtime_event(session.store, record)


def clear_companion_chat_service_caches() -> None:
    """For tests or hot reload when config path changes."""
    _companion_manager_for_resolved_model.cache_clear()


def _companion_runtime_config_fingerprint() -> str:
    cfg = global_config_loaded_from_config_yaml
    feats = cfg.app.features
    raw = feats.companion_transcript_compaction
    raw_json = json.dumps(raw, sort_keys=True) if raw is not None else ""
    parts = [
        "companion_scope_path_free_v1",
        str(feats.companion_default_context_mode),
        raw_json,
        str(feats.companion_transcript_llm_window_max_messages or ""),
        str(feats.companion_memory_bootstrap_type),
        str(feats.companion_ws_session_system_text or ""),
        # Bumps LRU when companion persistence semantics change (see CompanionConfig.repository_only_store_text).
        "companion_repo_only_store_v2",
        "companion_db_memory_documents_v4_orm",
        os.getenv("INTY_V2_PROTO_ASYNC_CHAT_FRONT_TIMEOUT_SEC", "600") or "",
        _companion_tool_call_model_yaml(cfg.agent),
    ]
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:32]


@lru_cache(maxsize=64)
def _companion_manager_for_resolved_model(
    chat_model_api_id: str,
    tool_model_api_id: str,
    runtime_fingerprint: str,
) -> CompanionManager:
    _ = runtime_fingerprint
    cfg = global_config_loaded_from_config_yaml
    feats = cfg.app.features
    api_key = cfg.agent.chat_llm_api_key or cfg.agent.api_key
    timeout_raw = os.getenv(
        # TODO(app-config-centralization): Move this to app.core.config, and do not use env var.
        "INTY_V2_PROTO_ASYNC_CHAT_FRONT_TIMEOUT_SEC", "600"
    ).strip()
    try:
        async_chat_timeout = float(timeout_raw) if timeout_raw else 600.0
    except ValueError:
        async_chat_timeout = 600.0
    chat_m = resolve_chat_text_model(chat_model_api_id)
    tool_m = resolve_chat_text_model(tool_model_api_id)
    llm = CompanionLLMConfig(
        api_key=api_key,
        api_base=cfg.agent.chat_llm_base_url or cfg.agent.base_url,
        default_model=chat_m,
        chat_model=chat_m,
        tool_model=tool_m,
        memory_model=chat_m,
        day_summary_model=chat_m,
        user_model=chat_m,
        soul_model=chat_m,
        async_chat_front_timeout_sec=async_chat_timeout,
    )
    tc_raw = feats.companion_transcript_compaction
    transcript_compaction = (
        TranscriptCompactionConfig.model_validate(tc_raw)
        if tc_raw is not None
        else None
    )
    db_url = (cfg.database.url or "").strip()
    if not db_url:
        raise RuntimeError(MEMORY_STORE_REGISTRY_REQUIRES_DSN)
    companion_cfg = CompanionConfig(
        memory_pg_dsn=db_url,
        llm=llm,
        default_context_mode=feats.companion_default_context_mode,
        transcript_compaction=transcript_compaction,
        transcript_llm_window_max_messages=feats.companion_transcript_llm_window_max_messages,
        repository_only_store_text=True,
        memory_bootstrap_type=feats.companion_memory_bootstrap_type,
    )
    return CompanionManager(companion_cfg)


def _mark_companion_ws_session_system_written_in_store(
    session: CompanionSession,
) -> None:
    rel = "context.json"
    raw = session.store.read_document_if_exists(rel)
    if raw is None or not str(raw).strip():
        return
    data = json.loads(raw)
    if not isinstance(data, dict):
        return
    data["companion_ws_session_system_written"] = True
    session.store.write_document(
        rel, json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    )


async def _maybe_append_companion_ws_session_system(
    *,
    session: CompanionSession,
    session_id: str | None,
) -> None:
    if not session_id or not str(session_id).strip():
        return
    if (
        session.config.memory_bootstrap_type
        != CompanionMemoryBootstrapType.USER_INTERACTIVE.value
    ):
        return
    from app.core.companion_harness.companion.models import load_context_meta
    from app.core.companion_harness.companion.utc import utc_iso_ts
    from app.core.companion_harness.memory.memory_store_scope import (
        DEFAULT_MEMORY_STORE_SCOPE_PATHS,
    )
    from app.services import chat_history_service

    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    meta = load_context_meta(store=session.store)
    if meta.workspace_bootstrap_user_interactive_completed:
        return
    if meta.companion_ws_session_system_written:
        return

    feats = global_config_loaded_from_config_yaml.app.features
    text = (feats.companion_ws_session_system_text or "").strip() or (
        DEFAULT_COMPANION_WS_SESSION_SYSTEM_TEXT
    )
    trace_id = str(uuid.uuid4())
    msg_uuid = str(uuid.uuid4())
    meta_row = {"messageType": "companion_ws_session_system"}

    await chat_history_service.add_system_message_async(
        session_id,
        text,
        meta_data=meta_row,
    )

    rel_tr = paths.transcript
    session.store.append_jsonl_record(
        rel_tr,
        {
            "role": "system",
            "content": text,
            "ts": utc_iso_ts(),
            "uuid": msg_uuid,
            "trace_id": trace_id,
            "source": "chat",
            "companion_ws_session_system": True,
        },
    )
    _mark_companion_ws_session_system_written_in_store(session)
    logger.info(
        "companion_ws_session_system_written user={} agent={} chat={}",
        session.user_id,
        session.companion_id,
        session.chat_id,
    )


async def _companion_session_for_api_turn(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    resolved_chat_model: GenAIModel,
    session_id: str | None,
) -> tuple[CompanionManager, CompanionSession, str, float, float]:
    chat_api_id = resolved_chat_model.id_on_provider
    tool_api_id = _companion_tool_model_api_id(chat_api_id)
    t_mgr0 = time.perf_counter()
    manager = _companion_manager_for_resolved_model(
        chat_api_id, tool_api_id, _companion_runtime_config_fingerprint()
    )
    session = manager.get_or_create_session(user_id, agent_id, str(chat_id))
    manager_session_ms = (time.perf_counter() - t_mgr0) * 1000.0
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
    t_ws0 = time.perf_counter()
    await _maybe_append_companion_ws_session_system(
        session=session,
        session_id=session_id,
    )
    ws_system_ms = (time.perf_counter() - t_ws0) * 1000.0
    return manager, session, chat_api_id, manager_session_ms, ws_system_ms


def _log_companion_api_turn_finished(
    *,
    track_path: str,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    chat_api_id: str,
    t0: float,
    manager_session_ms: float,
    ws_system_ms: float,
    run_turn_ms: float,
    user_chars: int,
    defer_memory_update: bool,
    out: CompanionTurnResult,
) -> None:
    logger.info(
        "companion_chat_turn finished path={} user={} agent={} chat={} model={} "
        "total_ms={:.0f} manager_session_ms={:.0f} ws_session_system_ms={:.0f} kernel_run_turn_ms={:.0f} "
        "user_chars={} defer_memory={} inty_trace_id={} user_msg_uuid={} "
        "langsmith_trace_id={} langsmith_run_id={}",
        track_path,
        user_id,
        agent_id,
        chat_id,
        chat_api_id,
        (time.perf_counter() - t0) * 1000.0,
        manager_session_ms,
        ws_system_ms,
        run_turn_ms,
        user_chars,
        defer_memory_update,
        out.trace_id,
        out.user_msg_uuid,
        out.langsmith_trace_id or "",
        out.langsmith_run_id or "",
    )


async def _run_companion_api_track_turn(
    *,
    track_path: str,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    resolved_chat_model: GenAIModel,
    user_chars: int,
    defer_memory_update: bool,
    session_id: str | None,
    run_track,
) -> CompanionTurnResult:
    cfg = global_config_loaded_from_config_yaml
    agent_cfg = cfg.agent
    api_base = (
        agent_cfg.chat_llm_base_url or agent_cfg.base_url or ""
    ).strip() or "https://openrouter.ai/api/v1"
    chat_api_id = resolved_chat_model.id_on_provider
    t0 = time.perf_counter()
    logger.debug(
        "companion_chat_turn start path={} user={} agent={} chat={} model={} api_base={} defer_memory={}",
        track_path,
        user_id,
        agent_id,
        chat_id,
        chat_api_id,
        api_base,
        defer_memory_update,
    )
    manager, session, chat_api_id, manager_session_ms, ws_system_ms = (
        await _companion_session_for_api_turn(
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat_id,
            resolved_chat_model=resolved_chat_model,
            session_id=session_id,
        )
    )
    t_rt0 = time.perf_counter()
    out = await run_track(manager, session)
    run_turn_ms = (time.perf_counter() - t_rt0) * 1000.0
    _log_companion_api_turn_finished(
        track_path=track_path,
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_id,
        chat_api_id=chat_api_id,
        t0=t0,
        manager_session_ms=manager_session_ms,
        ws_system_ms=ws_system_ms,
        run_turn_ms=run_turn_ms,
        user_chars=user_chars,
        defer_memory_update=defer_memory_update,
        out=out,
    )
    return out


async def run_user_chat(
    *,
    user_id: str,
    # TODO(cleanup): Move agent_id to CompanionIdentity.
    agent_id: str,
    chat_id: str | int,
    user_text: str,
    resolved_chat_model: GenAIModel,
    companion_identity: CompanionIdentity,
    defer_memory_update: bool = True,
    session_id: str | None = None,
    background_output_sink: BackgroundToolEventSink | None = None,
    preset_user_msg_uuid: str | None = None,
    implicit_signal_bundle: ImplicitSignalBundle | None = None,
    runtime_channel: CompanionRuntimeChannel = CompanionRuntimeChannel.APP,
    bootstrap_interim_output_sink: BootstrapInterimOutputSink | None = None,
) -> CompanionTurnResult:
    cfg = global_config_loaded_from_config_yaml
    agent_cfg = cfg.agent
    api_base = (
        agent_cfg.chat_llm_base_url or agent_cfg.base_url or ""
    ).strip() or "https://openrouter.ai/api/v1"
    chat_api_id = resolved_chat_model.id_on_provider
    t0 = time.perf_counter()
    logger.debug(
        "companion_chat_turn start path={} user={} agent={} chat={} model={} api_base={} defer_memory={}",
        "user_chat",
        user_id,
        agent_id,
        chat_id,
        chat_api_id,
        api_base,
        defer_memory_update,
    )
    manager, session, chat_api_id, manager_session_ms, ws_system_ms = (
        await _companion_session_for_api_turn(
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat_id,
            resolved_chat_model=resolved_chat_model,
            session_id=session_id,
        )
    )
    t_rt0 = time.perf_counter()
    out = await manager.run_user_chat_turn(
        session,
        user_text,
        defer_memory_update=defer_memory_update,
        background_output_sink=background_output_sink,
        preset_user_msg_uuid=preset_user_msg_uuid,
        runtime_context=TurnRuntimeContext(
            channel=runtime_channel,
            implicit_signal_bundle=implicit_signal_bundle,
        ),
        bootstrap_interim_output_sink=bootstrap_interim_output_sink,
    )
    run_turn_ms = (time.perf_counter() - t_rt0) * 1000.0
    _log_companion_api_turn_finished(
        track_path="user_chat",
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_id,
        chat_api_id=chat_api_id,
        t0=t0,
        manager_session_ms=manager_session_ms,
        ws_system_ms=ws_system_ms,
        run_turn_ms=run_turn_ms,
        user_chars=len(user_text),
        defer_memory_update=defer_memory_update,
        out=out,
    )
    return out


async def run_companion_implicit_sign_on_greeting_turn_for_api(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    user_text: str,
    resolved_chat_model: GenAIModel,
    implicit_signal_bundle: ImplicitSignalBundle,
    defer_memory_update: bool = True,
    session_id: str | None = None,
    background_output_sink: BackgroundToolEventSink | None = None,
    preset_user_msg_uuid: str | None = None,
    runtime_channel: CompanionRuntimeChannel = CompanionRuntimeChannel.APP,
) -> CompanionTurnResult:
    return await _run_companion_api_track_turn(
        track_path="implicit_sign_on_greeting",
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_id,
        resolved_chat_model=resolved_chat_model,
        user_chars=len(user_text),
        defer_memory_update=defer_memory_update,
        session_id=session_id,
        run_track=lambda manager, session: manager.run_implicit_sign_on_greeting_turn(
            session,
            user_text,
            defer_memory_update=defer_memory_update,
            background_output_sink=background_output_sink,
            preset_user_msg_uuid=preset_user_msg_uuid,
            runtime_context=TurnRuntimeContext(
                channel=runtime_channel,
                implicit_signal_bundle=implicit_signal_bundle,
            ),
        ),
    )


async def run_companion_inner_tick_proactive_chat_turn_for_api(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    resolved_chat_model: GenAIModel,
    defer_memory_update: bool = True,
    session_id: str | None = None,
    background_output_sink: BackgroundToolEventSink | None = None,
    preset_user_msg_uuid: str | None = None,
    implicit_signal_bundle: ImplicitSignalBundle | None = None,
    runtime_channel: CompanionRuntimeChannel = CompanionRuntimeChannel.APP,
) -> CompanionTurnResult:
    return await _run_companion_api_track_turn(
        track_path="inner_tick_proactive_chat",
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_id,
        resolved_chat_model=resolved_chat_model,
        user_chars=0,
        defer_memory_update=defer_memory_update,
        session_id=session_id,
        run_track=lambda manager, session: manager.run_inner_tick_proactive_chat_turn(
            session,
            defer_memory_update=defer_memory_update,
            background_output_sink=background_output_sink,
            preset_user_msg_uuid=preset_user_msg_uuid,
            runtime_context=TurnRuntimeContext(
                channel=runtime_channel,
                implicit_signal_bundle=implicit_signal_bundle,
            ),
        ),
    )


async def run_companion_inner_tick_scheduled_turn_for_api(
    *,
    scheduled_user_text: str,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    resolved_chat_model: GenAIModel,
    defer_memory_update: bool = True,
    session_id: str | None = None,
    background_output_sink: BackgroundToolEventSink | None = None,
    preset_user_msg_uuid: str | None = None,
    implicit_signal_bundle: ImplicitSignalBundle | None = None,
    runtime_channel: CompanionRuntimeChannel = CompanionRuntimeChannel.APP,
) -> CompanionTurnResult:
    assert (
        scheduled_user_text.strip()
    ), "run_companion_inner_tick_scheduled_turn_for_api requires non-empty scheduled_user_text"
    return await _run_companion_api_track_turn(
        track_path="inner_tick_scheduled",
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_id,
        resolved_chat_model=resolved_chat_model,
        user_chars=len(scheduled_user_text),
        defer_memory_update=defer_memory_update,
        session_id=session_id,
        run_track=lambda manager, session: manager.run_inner_tick_scheduled_turn(
            session,
            scheduled_user_text,
            defer_memory_update=defer_memory_update,
            background_output_sink=background_output_sink,
            preset_user_msg_uuid=preset_user_msg_uuid,
            runtime_context=TurnRuntimeContext(
                channel=runtime_channel,
                implicit_signal_bundle=implicit_signal_bundle,
            ),
        ),
    )


async def run_companion_inner_tick_maintenance_turn_for_api(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    resolved_chat_model: GenAIModel,
    defer_memory_update: bool = True,
    session_id: str | None = None,
    background_output_sink: BackgroundToolEventSink | None = None,
    preset_user_msg_uuid: str | None = None,
    implicit_signal_bundle: ImplicitSignalBundle | None = None,
    runtime_channel: CompanionRuntimeChannel = CompanionRuntimeChannel.APP,
) -> CompanionTurnResult:
    return await _run_companion_api_track_turn(
        track_path="inner_tick_maintenance",
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_id,
        resolved_chat_model=resolved_chat_model,
        user_chars=0,
        defer_memory_update=defer_memory_update,
        session_id=session_id,
        run_track=lambda manager, session: manager.run_inner_tick_maintenance_turn(
            session,
            defer_memory_update=defer_memory_update,
            background_output_sink=background_output_sink,
            preset_user_msg_uuid=preset_user_msg_uuid,
            runtime_context=TurnRuntimeContext(
                channel=runtime_channel,
                implicit_signal_bundle=implicit_signal_bundle,
            ),
        ),
    )


async def run_companion_chat_turn_for_api(
    *,
    user_id: str,
    # TODO(cleanup): Move agent_id to CompanionIdentity.
    agent_id: str,
    chat_id: str | int,
    user_text: str,
    resolved_chat_model: GenAIModel,
    companion_identity: CompanionIdentity,
    defer_memory_update: bool = True,
    session_id: str | None = None,
    background_output_sink: BackgroundToolEventSink | None = None,
    preset_user_msg_uuid: str | None = None,
    implicit_signal_bundle: ImplicitSignalBundle | None = None,
    inner_tick_turn: bool = False,
    inner_tick_activity: InnerTickActivity = InnerTickActivity.MAINTENANCE,
    runtime_channel: CompanionRuntimeChannel = CompanionRuntimeChannel.APP,
) -> CompanionTurnResult:
    """Legacy delegator; WebSocket handlers should call track-specific APIs."""
    common = {
        "user_id": user_id,
        "agent_id": agent_id,
        "chat_id": chat_id,
        "resolved_chat_model": resolved_chat_model,
        "defer_memory_update": defer_memory_update,
        "session_id": session_id,
        "background_output_sink": background_output_sink,
        "preset_user_msg_uuid": preset_user_msg_uuid,
        "implicit_signal_bundle": implicit_signal_bundle,
        "runtime_channel": runtime_channel,
    }
    if inner_tick_turn:
        match inner_tick_activity:
            case InnerTickActivity.PROACTIVE_CHAT:
                return (
                    await run_companion_inner_tick_proactive_chat_turn_for_api(
                        **common,
                    )
                )
            case InnerTickActivity.MAINTENANCE:
                return await run_companion_inner_tick_maintenance_turn_for_api(
                    **common,
                )
    if implicit_user_signed_on_chat_turn(
        implicit_signal_bundle=implicit_signal_bundle,
        inner_tick_turn=False,
    ):
        return await run_companion_implicit_sign_on_greeting_turn_for_api(
            user_text=user_text,
            implicit_signal_bundle=implicit_signal_bundle,
            **common,
        )
    return await run_user_chat(
        user_text=user_text,
        companion_identity=companion_identity,
        **common,
    )
