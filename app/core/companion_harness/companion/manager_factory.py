"""CompanionManager construction and LRU cache keyed by resolved chat/tool models."""

from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache

from app.core.llms.client import CompanionLLMConfig
from app.core.companion_harness.companion.manager import (
    CompanionConfig,
    CompanionManager,
)
from app.core.companion_harness.memory.memory_registry import (
    MEMORY_STORE_REGISTRY_REQUIRES_DSN,
)
from app.core.companion_harness.memory.transcript_compaction import (
    CompactionConfig as TranscriptCompactionConfig,
)
from app.core.config import global_config_loaded_from_config_yaml
from app.utils.models_catalog import resolve_chat_text_model

DEFAULT_COMPANION_WS_SESSION_SYSTEM_TEXT = (
    "（会话入线，内部指令）用户已进入本聊天。请在本轮及之后延续自然陪伴：可先简短问候，"
    "并温和邀请对方说说此刻状态或想聊的事；不要提及系统、连接、初始化、工具名。"
)


def companion_tool_call_model_yaml(agent: object) -> str:
    """Stripped ``AgentConfig.companion_tool_call_model``; empty means use chat model id."""
    return (getattr(agent, "companion_tool_call_model", "") or "").strip()


def companion_tool_model_api_id(chat_model_api_id: str) -> str:
    """OpenRouter-style id for tool rounds; defaults to chat model when YAML override is empty.

    TODO(#3398): Scope of separate tool model vs single chat model for user turns — epic #3398.
    """
    cfg = global_config_loaded_from_config_yaml
    raw = companion_tool_call_model_yaml(cfg.agent)
    if not raw:
        return chat_model_api_id
    return resolve_chat_text_model(raw).id_on_provider


def clear_companion_manager_cache() -> None:
    """For tests or hot reload when config path changes."""
    companion_manager_for_resolved_model.cache_clear()


def companion_runtime_config_fingerprint() -> str:
    cfg = global_config_loaded_from_config_yaml
    harness = cfg.agent.companion_harness
    raw = harness.transcript.compaction
    raw_json = json.dumps(raw, sort_keys=True) if raw is not None else ""
    parts = [
        "companion_scope_path_free_v1",
        str(harness.default_context_mode),
        raw_json,
        str(harness.transcript.llm_window_max_messages or ""),
        str(harness.memory_bootstrap_type),
        str(harness.ws.session_system_text or ""),
        "companion_repo_only_store_v2",
        "companion_db_memory_documents_v4_orm",
        os.getenv("INTY_V2_PROTO_ASYNC_CHAT_FRONT_TIMEOUT_SEC", "600") or "",
        companion_tool_call_model_yaml(cfg.agent),
    ]
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:32]


@lru_cache(maxsize=64)
def companion_manager_for_resolved_model(
    chat_model_api_id: str,
    tool_model_api_id: str,
    runtime_fingerprint: str,
) -> CompanionManager:
    _ = runtime_fingerprint
    cfg = global_config_loaded_from_config_yaml
    harness = cfg.agent.companion_harness
    api_key = cfg.agent.chat_llm_api_key or cfg.agent.api_key
    timeout_raw = os.getenv(
        "INTY_V2_PROTO_ASYNC_CHAT_FRONT_TIMEOUT_SEC",
        "600",
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
    tc_raw = harness.transcript.compaction
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
        default_context_mode=harness.default_context_mode,
        transcript_compaction=transcript_compaction,
        transcript_llm_window_max_messages=harness.transcript.llm_window_max_messages,
        repository_only_store_text=True,
        memory_bootstrap_type=harness.memory_bootstrap_type,
    )
    return CompanionManager(companion_cfg)
