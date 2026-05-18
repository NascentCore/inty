"""Route selected chat traffic through the agentic companion kernel (same as inty v2 REPL)."""

from __future__ import annotations

from collections.abc import Callable
import hashlib
import json
import os
import threading
import time
import uuid
from functools import lru_cache

from loguru import logger

from app.core.companion_harness.companion.llm_client import CompanionLLMConfig
from app.core.companion_harness.companion.turn_routes import (
    BackgroundToolEventSink,
)
from app.core.companion_harness.companion.manager import (
    CompanionConfig,
    CompanionManager,
    CompanionSession,
)
from app.core.companion_harness.memory.memory_registry import (
    MEMORY_STORE_REGISTRY_REQUIRES_DSN,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.ws_lifecycle_events import (
    normalize_received_message_uuid_for_lifecycle,
    record_user_signed_on,
    record_user_signed_out,
    record_ws_conn_dropped,
    resolve_client_local_ts_for_ws_lifecycle,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.companion.models import (
    CompanionTurnResult,
    InnerTickMode,
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


def companion_session_tool_bg_idle_event(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    resolved_chat_model: GenAIModel,
) -> threading.Event:
    """Return ``CompanionSession.tool_bg_idle`` for WebSocket inner-tick overlap checks."""
    chat_api_id = resolved_chat_model.id_on_provider
    tool_api_id = _companion_tool_model_api_id(chat_api_id)
    manager = _companion_manager_for_resolved_model(
        chat_api_id,
        tool_api_id,
        _companion_runtime_config_fingerprint(),
    )
    session = manager.get_or_create_session(user_id, agent_id, str(chat_id))
    return session.tool_bg_idle


def _companion_store_for_scope(
    scope: CompanionScope,
    *,
    resolved_chat_model: GenAIModel,
) -> MemoryStore:
    chat_api_id = resolved_chat_model.id_on_provider
    tool_api_id = _companion_tool_model_api_id(chat_api_id)
    manager = _companion_manager_for_resolved_model(
        chat_api_id,
        tool_api_id,
        _companion_runtime_config_fingerprint(),
    )
    session = manager.get_or_create_session(
        scope.user_id,
        scope.agent_id,
        scope.chat_id,
    )
    return session.store


def _lifecycle_ts_timezone_and_store(
    scope: CompanionScope,
    *,
    resolved_chat_model: GenAIModel,
    tc_box: list[object | None],
    dropped_at_utc: str | None,
) -> tuple[str, str, MemoryStore] | None:
    resolved = resolve_client_local_ts_for_ws_lifecycle(
        tc_box=tc_box,
        dropped_at_utc=dropped_at_utc,
    )
    if resolved is None:
        logger.warning(
            "companion_ws_lifecycle skipped missing client local ts user={} agent={} chat_id={}",
            scope.user_id,
            scope.agent_id,
            scope.chat_id,
        )
        return None
    ts, timezone_label = resolved
    store = _companion_store_for_scope(scope, resolved_chat_model=resolved_chat_model)
    return ts, timezone_label, store


def _record_companion_ws_lifecycle_best_effort(
    scope: CompanionScope,
    *,
    kind: str,
    op: Callable[[], None],
) -> None:
    """Append WS lifecycle JSONL without failing the WebSocket ack path."""
    try:
        op()
    except Exception:
        logger.warning(
            "companion_ws_lifecycle record failed kind={} user_id={} agent_id={} chat_id={}",
            kind,
            scope.user_id,
            scope.agent_id,
            scope.chat_id,
            exc_info=True,
        )


def record_companion_user_signed_on_ws_lifecycle(
    *,
    scope: CompanionScope,
    resolved_chat_model: GenAIModel,
    tc_box: list[object | None],
    received_message_uuid: str,
    ws_conn_id: str,
) -> None:
    def _do() -> None:
        packed = _lifecycle_ts_timezone_and_store(
            scope,
            resolved_chat_model=resolved_chat_model,
            tc_box=tc_box,
            dropped_at_utc=None,
        )
        if packed is None:
            return
        ts, timezone_label, store = packed
        record_user_signed_on(
            store,
            ts=ts,
            timezone_label=timezone_label,
            user_id=scope.user_id,
            agent_id=scope.agent_id,
            chat_id=scope.chat_id,
            received_message_uuid=normalize_received_message_uuid_for_lifecycle(
                received_message_uuid
            ),
            ws_conn_id=ws_conn_id,
        )

    _record_companion_ws_lifecycle_best_effort(
        scope, kind="user_signed_on", op=_do
    )


def record_companion_user_signed_out_ws_lifecycle(
    *,
    scope: CompanionScope,
    resolved_chat_model: GenAIModel,
    tc_box: list[object | None],
    received_message_uuid: str,
    ws_conn_id: str,
) -> None:
    def _do() -> None:
        packed = _lifecycle_ts_timezone_and_store(
            scope,
            resolved_chat_model=resolved_chat_model,
            tc_box=tc_box,
            dropped_at_utc=None,
        )
        if packed is None:
            return
        ts, timezone_label, store = packed
        record_user_signed_out(
            store,
            ts=ts,
            timezone_label=timezone_label,
            user_id=scope.user_id,
            agent_id=scope.agent_id,
            chat_id=scope.chat_id,
            received_message_uuid=normalize_received_message_uuid_for_lifecycle(
                received_message_uuid
            ),
            ws_conn_id=ws_conn_id,
        )

    _record_companion_ws_lifecycle_best_effort(
        scope, kind="user_signed_out", op=_do
    )


def record_companion_ws_conn_dropped_ws_lifecycle(
    *,
    scope: CompanionScope,
    resolved_chat_model: GenAIModel,
    tc_box: list[object | None],
    dropped_at_utc: str,
    received_message_uuid: str,
    ws_conn_id: str,
    ws_close_code: int | str,
    ws_close_reason: str,
) -> None:
    def _do() -> None:
        packed = _lifecycle_ts_timezone_and_store(
            scope,
            resolved_chat_model=resolved_chat_model,
            tc_box=tc_box,
            dropped_at_utc=dropped_at_utc,
        )
        if packed is None:
            return
        ts, timezone_label, store = packed
        record_ws_conn_dropped(
            store,
            ts=ts,
            timezone_label=timezone_label,
            user_id=scope.user_id,
            agent_id=scope.agent_id,
            chat_id=scope.chat_id,
            received_message_uuid=normalize_received_message_uuid_for_lifecycle(
                received_message_uuid
            ),
            ws_conn_id=ws_conn_id,
            ws_close_code=ws_close_code,
            ws_close_reason=ws_close_reason,
        )

    _record_companion_ws_lifecycle_best_effort(
        scope, kind="ws_conn_dropped", op=_do
    )


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
    api_key = (cfg.agent.chat_llm_api_key or "").strip() or cfg.agent.api_key
    timeout_raw = os.getenv(
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
        api_base=(
            cfg.agent.chat_llm_base_url or cfg.agent.base_url or ""
        ).strip()
        or "https://openrouter.ai/api/v1",
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


async def run_companion_chat_turn_for_api(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    user_text: str,
    resolved_chat_model: GenAIModel,
    defer_memory_update: bool = True,
    session_id: str | None = None,
    background_output_sink: BackgroundToolEventSink | None = None,
    preset_user_msg_uuid: str | None = None,
    implicit_signal_bundle: ImplicitSignalBundle | None = None,
    inner_tick_turn: bool = False,
    inner_tick_mode: InnerTickMode = InnerTickMode.MAINTENANCE,
) -> CompanionTurnResult:
    """
    Run one companion kernel turn for (user_id, agent_id, chat_id).

    ``app.features.companion_memory_bootstrap_type`` (default ``USER_INTERACTIVE``) controls
    companion bootstrap: ``NONE`` seeds minimal documents at session create and every message uses
    ``run_turn`` only; ``USER_INTERACTIVE`` seeds minimal docs and every message uses ``run_turn`` with
    interactive bootstrap tools until the model calls ``companion_bootstrap_user_interactive_complete``.

    ``resolved_chat_model`` must match ``select_chat_model`` for the same user and subscription
    (caller typically passes ``model_override`` from the chat completion path, e.g. WebSocket handler).
    """
    cfg = global_config_loaded_from_config_yaml
    agent_cfg = cfg.agent
    api_base = (
        agent_cfg.chat_llm_base_url or agent_cfg.base_url or ""
    ).strip() or "https://openrouter.ai/api/v1"
    t0 = time.perf_counter()
    chat_api_id = resolved_chat_model.id_on_provider
    tool_api_id = _companion_tool_model_api_id(chat_api_id)
    logger.debug(
        "companion_chat_turn start user={} agent={} chat={} model={} api_base={} defer_memory={}",
        user_id,
        agent_id,
        chat_id,
        chat_api_id,
        api_base,
        defer_memory_update,
    )
    t_mgr0 = time.perf_counter()
    manager = _companion_manager_for_resolved_model(
        chat_api_id, tool_api_id, _companion_runtime_config_fingerprint()
    )
    chat_key = str(chat_id)
    session = manager.get_or_create_session(user_id, agent_id, chat_key)
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
    t_rt0 = time.perf_counter()
    out = await manager.run_turn(
        session,
        user_text,
        inner_tick_turn=inner_tick_turn,
        inner_tick_mode=inner_tick_mode,
        defer_memory_update=defer_memory_update,
        background_output_sink=background_output_sink,
        preset_user_msg_uuid=preset_user_msg_uuid,
        implicit_signal_bundle=implicit_signal_bundle,
    )
    run_turn_ms = (time.perf_counter() - t_rt0) * 1000.0
    logger.info(
        "companion_chat_turn finished path=kernel user={} agent={} chat={} model={} "
        "total_ms={:.0f} manager_session_ms={:.0f} ws_session_system_ms={:.0f} kernel_run_turn_ms={:.0f} "
        "user_chars={} defer_memory={} inty_trace_id={} user_msg_uuid={} "
        "langsmith_trace_id={} langsmith_run_id={}",
        user_id,
        agent_id,
        chat_id,
        chat_api_id,
        (time.perf_counter() - t0) * 1000.0,
        manager_session_ms,
        ws_system_ms,
        run_turn_ms,
        len(user_text),
        defer_memory_update,
        out.trace_id,
        out.user_msg_uuid,
        out.langsmith_trace_id or "",
        out.langsmith_run_id or "",
    )
    return out
