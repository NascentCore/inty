"""Route selected chat traffic through the agentic companion kernel (same as inty v2 REPL)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from loguru import logger

from app.core.agentic_kernel.companion.llm_client import CompanionLLMClient, CompanionLLMConfig
from app.core.agentic_kernel.companion.manager import CompanionConfig, CompanionManager
from app.core.config import global_config_loaded_from_config_yaml
from app.core.model_selection import select_chat_model


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
    _companion_manager_for_subscription.cache_clear()


@lru_cache(maxsize=2)
def _companion_manager_for_subscription(is_subscribed: bool) -> CompanionManager:
    cfg = global_config_loaded_from_config_yaml
    feats = cfg.app.features
    base = Path(feats.companion_workspaces_base_dir).expanduser()
    base.mkdir(parents=True, exist_ok=True)
    model_id = select_chat_model(user=object(), is_subscribed=is_subscribed)
    llm = CompanionLLMConfig(
        api_key=cfg.agent.api_key,
        api_base=(cfg.agent.chat_llm_base_url or cfg.agent.base_url or "").strip()
        or "https://openrouter.ai/api/v1",
        default_model=model_id,
        chat_model=model_id,
        tool_model=model_id,
        memory_model=model_id,
        day_summary_model=model_id,
        user_model=model_id,
        soul_model=model_id,
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
    is_subscribed: bool,
    defer_memory_update: bool = True,
) -> str:
    """
    Run one companion kernel turn for (user_id, agent_id, chat_id).

    When the workspace is not yet initialized, the first user line is consumed by bootstrap.
    """
    manager = _companion_manager_for_subscription(is_subscribed)
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
