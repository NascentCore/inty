"""Route selected chat traffic through the agentic companion kernel (same as inty v2 REPL)."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

from loguru import logger

from app.core.agentic_kernel.companion.llm_client import CompanionLLMConfig
from app.core.agentic_kernel.companion.manager import CompanionConfig, CompanionManager
from app.core.agentic_kernel.companion.transcript_compaction import (
    CompactionConfig as TranscriptCompactionConfig,
)
from app.core.config import global_config_loaded_from_config_yaml


def clear_companion_chat_service_caches() -> None:
    """For tests or hot reload when config path changes."""
    _companion_manager_for_resolved_model.cache_clear()


def _companion_runtime_config_fingerprint() -> str:
    feats = global_config_loaded_from_config_yaml.app.features
    raw = feats.companion_transcript_compaction
    raw_json = json.dumps(raw, sort_keys=True) if raw is not None else ""
    parts = [
        str(feats.companion_workspaces_base_dir),
        str(feats.companion_default_context_mode),
        raw_json,
        str(feats.companion_transcript_llm_window_max_messages or ""),
        str(feats.companion_workspace_bootstrap_enabled),
        # Bumps LRU when companion persistence semantics change (see CompanionConfig.repository_only_workspace_text).
        "companion_repo_only_ws_v1",
        "companion_db_only_workspace_v3_orm",
    ]
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:32]


@lru_cache(maxsize=64)
def _companion_manager_for_resolved_model(
    resolved_chat_model_id: str, runtime_fingerprint: str
) -> CompanionManager:
    _ = runtime_fingerprint
    cfg = global_config_loaded_from_config_yaml
    feats = cfg.app.features
    base = Path(feats.companion_workspaces_base_dir).expanduser()
    api_key = (cfg.agent.chat_llm_api_key or "").strip() or cfg.agent.api_key
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
        workspace_bootstrap_enabled=feats.companion_workspace_bootstrap_enabled,
    )
    return CompanionManager(companion_cfg)


async def run_companion_chat_turn_for_api(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    user_text: str,
    resolved_chat_model_id: str,
    defer_memory_update: bool = True,
) -> str:
    """
    Run one companion kernel turn for (user_id, agent_id, chat_id).

    When the workspace is not yet initialized and ``app.features.companion_workspace_bootstrap_enabled``
    is true, the first user line is consumed by agentic bootstrap. When bootstrap is disabled,
    required workspace documents are seeded from package templates at session creation
    (``CompanionManager.get_or_create_session``), and this user line is handled by ``run_turn``.

    ``resolved_chat_model_id`` must match ``select_chat_model`` for the same user and subscription
    (caller typically passes ``model_override`` from the chat completion path, e.g. WebSocket handler).
    """
    manager = _companion_manager_for_resolved_model(
        resolved_chat_model_id, _companion_runtime_config_fingerprint()
    )
    chat_key = str(chat_id)
    session = manager.get_or_create_session(user_id, agent_id, chat_key)
    if not session.is_initialized:
        if session.config.workspace_bootstrap_enabled:
            logger.info(
                "companion_chat bootstrap user={} agent={} chat={}",
                user_id,
                agent_id,
                chat_id,
            )
            reply = await manager.bootstrap_session(session, user_text)
            if not session.is_initialized:
                raise RuntimeError(
                    "Companion workspace failed to initialize after bootstrap"
                )
            return reply
        if not session.is_initialized:
            raise RuntimeError(
                "Companion workspace not initialized (bootstrap disabled; expected seed at session create)"
            )
    return await manager.run_turn(
        session,
        user_text,
        defer_memory_update=defer_memory_update,
    )
