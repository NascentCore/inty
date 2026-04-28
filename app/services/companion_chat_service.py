"""Route selected chat traffic through the agentic companion kernel (same as inty v2 REPL)."""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from functools import lru_cache
from pathlib import Path

from loguru import logger

from app.core.agentic_kernel.companion.llm_client import (
    CompanionLLMConfig,
    async_tool_background_enabled_from_env,
)
from app.core.agentic_kernel.companion.turn_routes import BackgroundToolEventSink
from app.core.agentic_kernel.companion.manager import (
    CompanionConfig,
    CompanionManager,
    CompanionSession,
)
from app.core.agentic_kernel.companion.models import CompanionTurnResult
from app.core.agentic_kernel.companion.transcript_compaction import (
    CompactionConfig as TranscriptCompactionConfig,
)
from app.core.agentic_kernel.companion.bootstrap_user_interactive import (
    INTERACTIVE_BOOTSTRAP_WS_KICKOFF_USER_TEXT,
)
from app.core.config import global_config_loaded_from_config_yaml
from app.utils.config import CompanionWorkspaceBootstrapType

# Synthetic Path prefix for workspace_root joining; Postgres MemoryStore keys are
# user_id + companion_id + chat_id only (see SqlAlchemyMemoryRepository).
COMPANION_API_WORKSPACE_ROOT_PREFIX = Path("/var/lib/inty/companion_workspaces")

DEFAULT_COMPANION_WS_SESSION_SYSTEM_TEXT = (
    "（会话入线，内部指令）用户已进入本聊天。请在本轮及之后延续自然陪伴：可先简短问候，"
    "并温和邀请对方说说此刻状态或想聊的事；不要提及系统、连接、初始化、工具名。"
)


def clear_companion_chat_service_caches() -> None:
    """For tests or hot reload when config path changes."""
    _companion_manager_for_resolved_model.cache_clear()


def _companion_runtime_config_fingerprint() -> str:
    feats = global_config_loaded_from_config_yaml.app.features
    raw = feats.companion_transcript_compaction
    raw_json = json.dumps(raw, sort_keys=True) if raw is not None else ""
    parts = [
        str(COMPANION_API_WORKSPACE_ROOT_PREFIX),
        str(feats.companion_default_context_mode),
        raw_json,
        str(feats.companion_transcript_llm_window_max_messages or ""),
        str(feats.companion_workspace_bootstrap_type),
        str(feats.companion_ws_session_system_text or ""),
        # Bumps LRU when companion persistence semantics change (see CompanionConfig.repository_only_workspace_text).
        "companion_repo_only_ws_v1",
        "companion_db_only_workspace_v3_orm",
        str(async_tool_background_enabled_from_env()),
        os.getenv("INTY_V2_PROTO_ASYNC_CHAT_FRONT_TIMEOUT_SEC", "600") or "",
    ]
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:32]


@lru_cache(maxsize=64)
def _companion_manager_for_resolved_model(
    resolved_chat_model_id: str, runtime_fingerprint: str
) -> CompanionManager:
    _ = runtime_fingerprint
    cfg = global_config_loaded_from_config_yaml
    feats = cfg.app.features
    base = COMPANION_API_WORKSPACE_ROOT_PREFIX.expanduser()
    api_key = (cfg.agent.chat_llm_api_key or "").strip() or cfg.agent.api_key
    timeout_raw = os.getenv("INTY_V2_PROTO_ASYNC_CHAT_FRONT_TIMEOUT_SEC", "600").strip()
    try:
        async_chat_timeout = float(timeout_raw) if timeout_raw else 600.0
    except ValueError:
        async_chat_timeout = 600.0
    llm = CompanionLLMConfig(
        api_key=api_key,
        api_base=(cfg.agent.chat_llm_base_url or cfg.agent.base_url or "").strip()
        or "https://openrouter.ai/api/v1",
        default_model=resolved_chat_model_id,
        chat_model=resolved_chat_model_id,
        tool_model=resolved_chat_model_id,
        memory_model=resolved_chat_model_id,
        day_summary_model=resolved_chat_model_id,
        user_model=resolved_chat_model_id,
        soul_model=resolved_chat_model_id,
        enable_async_tool_background=async_tool_background_enabled_from_env(),
        async_chat_front_timeout_sec=async_chat_timeout,
    )
    tc_raw = feats.companion_transcript_compaction
    transcript_compaction = (
        TranscriptCompactionConfig.model_validate(tc_raw)
        if tc_raw is not None
        else None
    )
    companion_cfg = CompanionConfig(
        workspaces_base_dir=str(base),
        memory_pg_dsn=cfg.database.url,
        llm=llm,
        default_context_mode=feats.companion_default_context_mode,
        transcript_compaction=transcript_compaction,
        transcript_llm_window_max_messages=feats.companion_transcript_llm_window_max_messages,
        repository_only_workspace_text=True,
        workspace_bootstrap_type=feats.companion_workspace_bootstrap_type,
    )
    return CompanionManager(companion_cfg)


def _mark_companion_ws_session_system_written_in_store(
    session: CompanionSession,
) -> None:
    from app.core.agentic_kernel.companion.companion_tool_runtime import (
        resolve_under_workspace,
    )

    root_r = session.workspace_path.resolve()
    rel = resolve_under_workspace(root_r, "context.json").relative_to(root_r).as_posix()
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
        session.config.workspace_bootstrap_type
        != CompanionWorkspaceBootstrapType.USER_INTERACTIVE.value
    ):
        return
    from app.core.agentic_kernel.companion.models import load_context_meta
    from app.core.agentic_kernel.companion.utc import utc_iso_ts
    from app.core.agentic_kernel.companion.workspace import WorkspacePaths
    from app.services import chat_history_service

    paths = WorkspacePaths(root=session.workspace_path.resolve())
    meta = load_context_meta(paths.context_json, store=session.store)
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

    root_r = session.workspace_path.resolve()
    rel_tr = paths.transcript.relative_to(root_r).as_posix()
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


def _mark_companion_ws_interactive_kickoff_sent_in_store(
    session: CompanionSession,
) -> None:
    from app.core.agentic_kernel.companion.companion_tool_runtime import (
        resolve_under_workspace,
    )

    root_r = session.workspace_path.resolve()
    rel = resolve_under_workspace(root_r, "context.json").relative_to(root_r).as_posix()
    raw = session.store.read_document_if_exists(rel)
    if raw is None or not str(raw).strip():
        return
    data = json.loads(raw)
    if not isinstance(data, dict):
        return
    data["companion_ws_interactive_kickoff_sent"] = True
    session.store.write_document(
        rel, json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    )


async def run_companion_interactive_bootstrap_kickoff_for_ws(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    session_id: str,
    resolved_chat_model_id: str,
) -> str | None:
    """
    One-shot assistant turn when USER_INTERACTIVE bootstrap is incomplete and WS kickoff not yet sent.

    Uses a fixed internal user line so the model opens the relationship phase without a real user message.
    """
    feats = global_config_loaded_from_config_yaml.app.features
    if (
        feats.companion_workspace_bootstrap_type
        != CompanionWorkspaceBootstrapType.USER_INTERACTIVE.value
    ):
        return None
    manager = _companion_manager_for_resolved_model(
        resolved_chat_model_id, _companion_runtime_config_fingerprint()
    )
    chat_key = str(chat_id)
    session = manager.get_or_create_session(user_id, agent_id, chat_key)
    if not session.is_initialized:
        return None
    from app.core.agentic_kernel.companion.models import load_context_meta
    from app.core.agentic_kernel.companion.workspace import WorkspacePaths

    paths = WorkspacePaths(root=session.workspace_path.resolve())
    meta = load_context_meta(paths.context_json, store=session.store)
    if meta.workspace_bootstrap_user_interactive_completed:
        return None
    if meta.companion_ws_interactive_kickoff_sent:
        return None

    t0 = time.perf_counter()
    t_ws0 = time.perf_counter()
    await _maybe_append_companion_ws_session_system(
        session=session,
        session_id=session_id,
    )
    ws_system_ms = (time.perf_counter() - t_ws0) * 1000.0
    t_rt0 = time.perf_counter()
    turn = await manager.run_turn(
        session,
        INTERACTIVE_BOOTSTRAP_WS_KICKOFF_USER_TEXT,
        defer_memory_update=True,
    )
    reply = turn.assistant_text
    run_turn_ms = (time.perf_counter() - t_rt0) * 1000.0
    total_ms = (time.perf_counter() - t0) * 1000.0
    if not reply or not str(reply).strip():
        logger.warning(
            "companion_ws_interactive_kickoff empty reply user={} agent={} chat={} total_ms={:.0f} ws_session_system_ms={:.0f} kernel_run_turn_ms={:.0f}",
            user_id,
            agent_id,
            chat_id,
            total_ms,
            ws_system_ms,
            run_turn_ms,
        )
        return None
    # Mark before chat_history persist so reconnect does not run a second run_turn (transcript already
    # has this turn). If add_ai_message later fails, operators may see transcript vs chat_history skew.
    _mark_companion_ws_interactive_kickoff_sent_in_store(session)
    logger.info(
        "companion_ws_interactive_kickoff_sent user={} agent={} chat={} total_ms={:.0f} ws_session_system_ms={:.0f} kernel_run_turn_ms={:.0f}",
        user_id,
        agent_id,
        chat_id,
        total_ms,
        ws_system_ms,
        run_turn_ms,
    )
    return reply


async def run_companion_chat_turn_for_api(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    user_text: str,
    resolved_chat_model_id: str,
    defer_memory_update: bool = True,
    session_id: str | None = None,
    background_output_sink: BackgroundToolEventSink | None = None,
    preset_user_msg_uuid: str | None = None,
) -> CompanionTurnResult:
    """
    Run one companion kernel turn for (user_id, agent_id, chat_id).

    ``app.features.companion_workspace_bootstrap_type`` (default ``USER_INTERACTIVE``) controls
    companion bootstrap: ``NONE`` seeds minimal documents at session create and every message uses
    ``run_turn`` only; ``USER_INTERACTIVE`` seeds minimal docs and every message uses ``run_turn`` with
    interactive bootstrap tools until the model calls ``companion_bootstrap_user_interactive_complete``.

    ``resolved_chat_model_id`` must match ``select_chat_model`` for the same user and subscription
    (caller typically passes ``model_override`` from the chat completion path, e.g. WebSocket handler).
    """
    cfg = global_config_loaded_from_config_yaml
    agent_cfg = cfg.agent
    api_base = (
        agent_cfg.chat_llm_base_url or agent_cfg.base_url or ""
    ).strip() or "https://openrouter.ai/api/v1"
    t0 = time.perf_counter()
    logger.debug(
        "companion_chat_turn start user={} agent={} chat={} model={} api_base={} defer_memory={}",
        user_id,
        agent_id,
        chat_id,
        resolved_chat_model_id,
        api_base,
        defer_memory_update,
    )
    t_mgr0 = time.perf_counter()
    manager = _companion_manager_for_resolved_model(
        resolved_chat_model_id, _companion_runtime_config_fingerprint()
    )
    chat_key = str(chat_id)
    session = manager.get_or_create_session(user_id, agent_id, chat_key)
    manager_session_ms = (time.perf_counter() - t_mgr0) * 1000.0
    if not session.is_initialized:
        if (
            session.config.workspace_bootstrap_type
            == CompanionWorkspaceBootstrapType.USER_INTERACTIVE.value
        ):
            raise RuntimeError(
                "Companion workspace not seeded (interactive bootstrap requires minimal documents in store)"
            )
        raise RuntimeError(
            "Companion workspace not initialized (expected minimal seed at session create)"
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
        defer_memory_update=defer_memory_update,
        background_output_sink=background_output_sink,
        preset_user_msg_uuid=preset_user_msg_uuid,
    )
    run_turn_ms = (time.perf_counter() - t_rt0) * 1000.0
    logger.info(
        "companion_chat_turn finished path=kernel user={} agent={} chat={} model={} total_ms={:.0f} manager_session_ms={:.0f} ws_session_system_ms={:.0f} kernel_run_turn_ms={:.0f} user_chars={} defer_memory={}",
        user_id,
        agent_id,
        chat_id,
        resolved_chat_model_id,
        (time.perf_counter() - t0) * 1000.0,
        manager_session_ms,
        ws_system_ms,
        run_turn_ms,
        len(user_text),
        defer_memory_update,
    )
    return out
