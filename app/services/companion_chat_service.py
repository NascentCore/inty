"""Route selected chat traffic through the agentic companion kernel (same as inty v2 REPL).

Companion concurrency (scope vs presence): ``session.Coordinator``; prototype single
presence per paired user — ``companion_harness`` AGENTS.md「Concurrency (prototype)」.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from typing import Any

from loguru import logger

from app.core.companion_harness.companion.manager_factory import (
    DEFAULT_COMPANION_WS_SESSION_SYSTEM_TEXT,
    clear_companion_manager_cache,
    companion_manager_for_resolved_model,
    companion_runtime_config_fingerprint,
    companion_tool_model_api_id,
)
from app.core.companion_harness.companion.runtime_events import (
    append_runtime_event,
)
from app.core.companion_harness.companion.dreaming_observability import (
    DreamingBatchOutcome,
)
from app.core.companion_harness.runtime.dreaming_batch import (
    run_dreaming_batch_if_due,
)
from app.core.companion_harness.companion.turn_routes import (
    BackgroundToolEventSink,
    BootstrapInterimOutputSink,
)
from app.core.companion_harness.companion.manager import (
    CompanionManager,
    CompanionSession,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.companion.implicit_signal_messages import (
    implicit_user_signed_on_chat_turn,
)
from app.core.companion_harness.companion.models import (
    CompanionTurnResult,
    InnerTickActivity,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)
from app.core.config import global_config_loaded_from_config_yaml
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.utils.config import CompanionMemoryBootstrapType
from app.utils.models_catalog import GenAIModel


def clear_companion_chat_service_caches() -> None:
    """For tests or hot reload when config path changes."""
    clear_companion_manager_cache()


def companion_memory_store_if_ready(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    resolved_chat_model: GenAIModel,
) -> MemoryStore | None:
    """Return the session MemoryStore when minimal companion documents are initialized."""
    chat_api_id = resolved_chat_model.id_on_provider
    tool_api_id = companion_tool_model_api_id(chat_api_id)
    manager = companion_manager_for_resolved_model(
        chat_api_id,
        tool_api_id,
        companion_runtime_config_fingerprint(),
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
    """Return ``CompanionSession.tool_bg_idle`` for WebSocket inner-tick overlap checks.

    TODO(tool-bg-idle-starves-user-chat): Hung maintenance ``tool_background`` clears this event;
    the next user or proactive turn blocks in ``run_turn`` while holding ``turn_lock``.
    https://github.com/NascentCore/inty/issues/3123
    """
    chat_api_id = resolved_chat_model.id_on_provider
    tool_api_id = companion_tool_model_api_id(chat_api_id)
    manager = companion_manager_for_resolved_model(
        chat_api_id,
        tool_api_id,
        companion_runtime_config_fingerprint(),
    )
    session = manager.get_or_create_session(user_id, agent_id, str(chat_id))
    return session.tool_bg_idle


def run_dreaming_batch_for_api(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    resolved_chat_model: GenAIModel,
    dreaming_idle_seconds: int,
) -> DreamingBatchOutcome:
    """Resolve ``CompanionSession`` and run ``run_dreaming_batch_if_due``."""
    chat_api_id = resolved_chat_model.id_on_provider
    tool_api_id = companion_tool_model_api_id(chat_api_id)
    manager = companion_manager_for_resolved_model(
        chat_api_id,
        tool_api_id,
        companion_runtime_config_fingerprint(),
    )
    session = manager.get_or_create_session(user_id, agent_id, str(chat_id))
    return run_dreaming_batch_if_due(
        session,
        idle_seconds=dreaming_idle_seconds,
    )


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
    tool_api_id = companion_tool_model_api_id(chat_api_id)
    manager = companion_manager_for_resolved_model(
        chat_api_id,
        tool_api_id,
        companion_runtime_config_fingerprint(),
    )
    session = manager.get_or_create_session(user_id, agent_id, str(chat_id))
    append_runtime_event(session.store, record)


def _mark_companion_ws_session_system_written_in_store(
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

    harness = global_config_loaded_from_config_yaml.agent.companion_harness
    text = (harness.ws.session_system_text or "").strip() or (
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
    tool_api_id = companion_tool_model_api_id(chat_api_id)
    t_mgr0 = time.perf_counter()
    manager = companion_manager_for_resolved_model(
        chat_api_id, tool_api_id, companion_runtime_config_fingerprint()
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


def _companion_manager_session_ref(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    resolved_chat_model: GenAIModel,
) -> tuple[CompanionManager, CompanionSession]:
    """Lightweight manager + session lookup for scope lock acquisition (no ws_system)."""
    chat_api_id = resolved_chat_model.id_on_provider
    tool_api_id = companion_tool_model_api_id(chat_api_id)
    manager = companion_manager_for_resolved_model(
        chat_api_id, tool_api_id, companion_runtime_config_fingerprint()
    )
    session = manager.get_or_create_session(user_id, agent_id, str(chat_id))
    return manager, session


async def resolve_companion_session_for_api_turn(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    resolved_chat_model: GenAIModel,
    session_id: str | None,
) -> CompanionSession:
    """Resolve ``CompanionSession`` for scope turn locking without running a turn."""
    _ = session_id
    _, session = _companion_manager_session_ref(
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_id,
        resolved_chat_model=resolved_chat_model,
    )
    return session


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
    out: CompanionTurnResult,
) -> None:
    logger.info(
        "companion_chat_turn finished path={} user={} agent={} chat={} model={} "
        "total_ms={:.0f} manager_session_ms={:.0f} ws_session_system_ms={:.0f} kernel_run_turn_ms={:.0f} "
        "user_chars={} inty_trace_id={} user_msg_uuid={} "
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
        out.trace_id,
        out.user_msg_uuid,
        out.langsmith_trace_id or "",
        out.langsmith_run_id or "",
    )


async def _execute_companion_api_track_turn(
    *,
    track_path: str,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    chat_api_id: str,
    user_chars: int,
    t0: float,
    manager_session_ms: float,
    ws_system_ms: float,
    manager: CompanionManager,
    session: CompanionSession,
    run_track,
) -> CompanionTurnResult:
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
        out=out,
    )
    return out


async def run_companion_api_track_turn_with_lock_held(
    *,
    track_path: str,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    resolved_chat_model: GenAIModel,
    user_chars: int,
    session_id: str | None,
    run_track,
) -> CompanionTurnResult:
    """Run one API track turn; caller must already hold ``session.turn_lock``."""
    cfg = global_config_loaded_from_config_yaml
    agent_cfg = cfg.agent
    api_base = (
        agent_cfg.chat_llm_base_url or agent_cfg.base_url or ""
    ).strip() or "https://openrouter.ai/api/v1"
    chat_api_id = resolved_chat_model.id_on_provider
    t0 = time.perf_counter()
    logger.debug(
        "companion_chat_turn start path={} user={} agent={} chat={} model={} api_base={}",
        track_path,
        user_id,
        agent_id,
        chat_id,
        chat_api_id,
        api_base,
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
    return await _execute_companion_api_track_turn(
        track_path=track_path,
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_id,
        chat_api_id=chat_api_id,
        user_chars=user_chars,
        t0=t0,
        manager_session_ms=manager_session_ms,
        ws_system_ms=ws_system_ms,
        manager=manager,
        session=session,
        run_track=run_track,
    )


async def _run_companion_api_track_turn(
    *,
    track_path: str,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    resolved_chat_model: GenAIModel,
    user_chars: int,
    session_id: str | None,
    run_track,
) -> CompanionTurnResult:
    _, session = _companion_manager_session_ref(
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_id,
        resolved_chat_model=resolved_chat_model,
    )
    async with session.turn_lock:
        return await run_companion_api_track_turn_with_lock_held(
            track_path=track_path,
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat_id,
            resolved_chat_model=resolved_chat_model,
            user_chars=user_chars,
            session_id=session_id,
            run_track=run_track,
        )


# TODO(companion-multimodal-user-turn): Phase 1b — replace ``user_text: str`` with
# https://github.com/NascentCore/inty/issues/3293
# ``user_turn: CompanionUserTurnInput`` (text + image_data_urls). Gate at entry:
# raise ``CompanionMultimodalNotSupportedError`` when images present but
# ``not chat_model_accepts_image_input(resolved_chat_model)``. Keep multimodal
# tail assembly in companion harness turn pipeline.
async def run_user_chat(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    user_text: str,
    resolved_chat_model: GenAIModel,
    session_id: str | None = None,
    background_output_sink: BackgroundToolEventSink | None = None,
    preset_user_msg_uuid: str | None = None,
    implicit_signal_bundle: ImplicitSignalBundle | None = None,
    runtime_channel: ChannelKind = ChannelKind.APP_WS,
    bootstrap_interim_output_sink: BootstrapInterimOutputSink | None = None,
) -> CompanionTurnResult:
    return await _run_companion_api_track_turn(
        track_path="user_chat",
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_id,
        resolved_chat_model=resolved_chat_model,
        user_chars=len(user_text),
        session_id=session_id,
        run_track=lambda manager, session: manager.run_user_chat_turn(
            session,
            user_text,
            background_output_sink=background_output_sink,
            preset_user_msg_uuid=preset_user_msg_uuid,
            runtime_context=TurnRuntimeContext(
                channel=runtime_channel,
                implicit_signal_bundle=implicit_signal_bundle,
            ),
            bootstrap_interim_output_sink=bootstrap_interim_output_sink,
        ),
    )


async def run_companion_implicit_sign_on_greeting_turn_for_api(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    user_text: str,
    resolved_chat_model: GenAIModel,
    implicit_signal_bundle: ImplicitSignalBundle,
    session_id: str | None = None,
    background_output_sink: BackgroundToolEventSink | None = None,
    preset_user_msg_uuid: str | None = None,
    runtime_channel: ChannelKind = ChannelKind.APP_WS,
) -> CompanionTurnResult:
    return await _run_companion_api_track_turn(
        track_path="implicit_sign_on_greeting",
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_id,
        resolved_chat_model=resolved_chat_model,
        user_chars=len(user_text),
        session_id=session_id,
        run_track=lambda manager, session: manager.run_implicit_sign_on_greeting_turn(
            session,
            user_text,
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
    session_id: str | None = None,
    background_output_sink: BackgroundToolEventSink | None = None,
    preset_user_msg_uuid: str | None = None,
    implicit_signal_bundle: ImplicitSignalBundle | None = None,
    runtime_channel: ChannelKind = ChannelKind.APP_WS,
) -> CompanionTurnResult:
    return await _run_companion_api_track_turn(
        track_path="inner_tick_proactive_chat",
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_id,
        resolved_chat_model=resolved_chat_model,
        user_chars=0,
        session_id=session_id,
        run_track=lambda manager, session: manager.run_inner_tick_proactive_chat_turn(
            session,
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
    session_id: str | None = None,
    background_output_sink: BackgroundToolEventSink | None = None,
    preset_user_msg_uuid: str | None = None,
    implicit_signal_bundle: ImplicitSignalBundle | None = None,
    runtime_channel: ChannelKind = ChannelKind.APP_WS,
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
        session_id=session_id,
        run_track=lambda manager, session: manager.run_inner_tick_scheduled_turn(
            session,
            scheduled_user_text,
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
    session_id: str | None = None,
    background_output_sink: BackgroundToolEventSink | None = None,
    preset_user_msg_uuid: str | None = None,
    implicit_signal_bundle: ImplicitSignalBundle | None = None,
    runtime_channel: ChannelKind = ChannelKind.APP_WS,
) -> CompanionTurnResult:
    return await _run_companion_api_track_turn(
        track_path="inner_tick_maintenance",
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_id,
        resolved_chat_model=resolved_chat_model,
        user_chars=0,
        session_id=session_id,
        run_track=lambda manager, session: manager.run_inner_tick_maintenance_turn(
            session,
            background_output_sink=background_output_sink,
            preset_user_msg_uuid=preset_user_msg_uuid,
            runtime_context=TurnRuntimeContext(
                channel=runtime_channel,
                implicit_signal_bundle=implicit_signal_bundle,
            ),
        ),
    )


async def run_inner_tick_autonomy(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    resolved_chat_model: GenAIModel,
    session_id: str | None = None,
    background_output_sink: BackgroundToolEventSink | None = None,
    preset_user_msg_uuid: str | None = None,
    implicit_signal_bundle: ImplicitSignalBundle | None = None,
    runtime_channel: ChannelKind = ChannelKind.APP_WS,
) -> CompanionTurnResult:
    """AUTONOMY inner-tick: silent self-directed turn; assistant_text is not delivered to the user."""
    return await _run_companion_api_track_turn(
        track_path="inner_tick_autonomy",
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_id,
        resolved_chat_model=resolved_chat_model,
        user_chars=0,
        session_id=session_id,
        run_track=lambda manager, session: manager.run_inner_tick_autonomy_turn(
            session,
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
    agent_id: str,
    chat_id: str | int,
    user_text: str,
    resolved_chat_model: GenAIModel,
    session_id: str | None = None,
    background_output_sink: BackgroundToolEventSink | None = None,
    preset_user_msg_uuid: str | None = None,
    implicit_signal_bundle: ImplicitSignalBundle | None = None,
    inner_tick_turn: bool = False,
    inner_tick_activity: InnerTickActivity = InnerTickActivity.MAINTENANCE,
    runtime_channel: ChannelKind = ChannelKind.APP_WS,
) -> CompanionTurnResult:
    """Legacy delegator; WebSocket handlers should call track-specific APIs."""
    common = {
        "user_id": user_id,
        "agent_id": agent_id,
        "chat_id": chat_id,
        "resolved_chat_model": resolved_chat_model,
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
            case InnerTickActivity.AUTONOMY:
                return await run_inner_tick_autonomy(**common)
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
        **common,
    )
