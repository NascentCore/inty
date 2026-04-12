"""Route selected chat traffic through the agentic companion kernel (same as inty v2 REPL)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from loguru import logger

from app.core.agentic_kernel.companion.inner_tick import (
    next_companion_inner_tick_wait_seconds,
)
from app.core.agentic_kernel.companion.llm_client import CompanionLLMConfig
from app.core.agentic_kernel.companion.manager import CompanionConfig, CompanionManager
from app.core.config import global_config_loaded_from_config_yaml


@lru_cache(maxsize=1)
def _companion_agent_id_allowlist() -> frozenset[str]:
    raw = global_config_loaded_from_config_yaml.app.features.chat_use_companion_kernel_agent_ids
    if not raw:
        return frozenset()
    return frozenset(str(x).strip() for x in raw if str(x).strip())


def use_companion_kernel_for_agent(agent_id: str) -> bool:
    allow = _companion_agent_id_allowlist()
    return bool(allow) and agent_id in allow


def clear_companion_chat_service_caches() -> None:
    """For tests or hot reload when config path changes."""
    _companion_agent_id_allowlist.cache_clear()
    _companion_manager_for_resolved_model.cache_clear()


@lru_cache(maxsize=32)
def _companion_manager_for_resolved_model(resolved_chat_model_id: str) -> CompanionManager:
    cfg = global_config_loaded_from_config_yaml
    feats = cfg.app.features
    base = Path(feats.companion_workspaces_base_dir).expanduser()
    base.mkdir(parents=True, exist_ok=True)
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
    companion_cfg = CompanionConfig(
        workspaces_base_dir=str(base),
        memory_pg_dsn=cfg.database.url,
        llm=llm,
        default_context_mode=feats.companion_default_context_mode,
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

    When the workspace is not yet initialized, the first user line is consumed by bootstrap.

    ``resolved_chat_model_id`` must match ``select_chat_model`` for the same user and subscription
    (caller typically passes ``model_override`` from ``agent_chat_completions``).
    """
    manager = _companion_manager_for_resolved_model(resolved_chat_model_id)
    chat_key = str(chat_id)
    session = manager.get_or_create_session(user_id, agent_id, chat_key)
    if not session.is_initialized:
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
    return await manager.run_turn(
        session,
        user_text,
        defer_memory_update=defer_memory_update,
    )


def companion_ws_inner_tick_wait_seconds(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    resolved_chat_model_id: str,
    last_inner_fire_monotonic: float | None,
    last_chat_turn_complete_monotonic: float | None,
) -> float:
    feats = global_config_loaded_from_config_yaml.app.features
    manager = _companion_manager_for_resolved_model(resolved_chat_model_id)
    session = manager.get_or_create_session(user_id, agent_id, str(chat_id))
    return next_companion_inner_tick_wait_seconds(
        session.workspace_path,
        session.store,
        last_inner_fire_monotonic=last_inner_fire_monotonic,
        last_chat_turn_complete_monotonic=last_chat_turn_complete_monotonic,
        first_after_user_seconds=feats.companion_ws_inner_tick_first_after_user_seconds,
        min_gap_seconds=feats.companion_ws_inner_tick_min_gap_seconds,
        min_transcript_messages=feats.companion_ws_inner_tick_min_transcript_messages,
        poll_cap_seconds=feats.companion_ws_inner_tick_poll_cap_seconds,
        blocked_max_seconds=feats.companion_ws_inner_tick_blocked_max_seconds,
    )


async def run_companion_inner_tick_turn_for_api(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    resolved_chat_model_id: str,
) -> str | None:
    manager = _companion_manager_for_resolved_model(resolved_chat_model_id)
    session = manager.get_or_create_session(user_id, agent_id, str(chat_id))
    if not session.is_initialized:
        return None
    return await manager.run_turn(
        session,
        "",
        inner_tick_turn=True,
        defer_memory_update=True,
    )
