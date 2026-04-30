"""记忆更新 adapter: 读 prototype env vars, 委托 kernel memory_pipeline。"""

from __future__ import annotations

import os
from typing import Any

from loguru import logger

from app.core.agentic_kernel.companion.memory_pipeline import (
    MemoryPipelineConfig,
    memory_update_after_turn as _kernel_memory_update,
    schedule_memory_update_after_turn as _kernel_schedule_memory_update,
)

from .client import complete, day_summary_model, memory_model, soul_model, user_model
from .memory_store_registry import get_memory_store
from .paths import WorkspacePaths
from .utc import local_date_str


def _positive_int_env(env_name: str, *, default: int = 100) -> int:
    raw = os.getenv(env_name, str(default)).strip()
    if not raw:
        return default
    try:
        n = int(raw, 10)
    except ValueError as e:
        raise ValueError(f"{env_name} must be a positive integer, got {raw!r}") from e
    if n < 1:
        raise ValueError(f"{env_name} must be >= 1, got {n}")
    return n


def _env_disabled(env_name: str) -> bool:
    return os.getenv(env_name, "").strip().lower() in ("1", "true", "yes")


def _soul_fundamental_signal_gate_enabled() -> bool:
    val = (
        os.getenv("INTY_V2_PROTO_SOUL_UPDATE_REQUIRE_FUNDAMENTAL_SIGNAL", "1")
        .strip()
        .lower()
    )
    return val not in ("0", "false", "no", "off")


def _build_config() -> MemoryPipelineConfig:
    return MemoryPipelineConfig(
        day_summary_every_n_turns=_positive_int_env(
            "INTY_V2_PROTO_DAY_SUMMARY_EVERY_N_TURNS", default=100
        ),
        memory_update_every_n_turns=_positive_int_env(
            "INTY_V2_PROTO_MEMORY_UPDATE_EVERY_N_TURNS", default=100
        ),
        user_update_every_n_turns=_positive_int_env(
            "INTY_V2_PROTO_USER_UPDATE_EVERY_N_TURNS", default=100
        ),
        soul_update_every_n_turns=_positive_int_env(
            "INTY_V2_PROTO_SOUL_UPDATE_EVERY_N_TURNS", default=100
        ),
        day_summary_disabled=_env_disabled("INTY_V2_PROTO_DAY_SUMMARY_DISABLED"),
        user_update_disabled=_env_disabled("INTY_V2_PROTO_USER_UPDATE_DISABLED"),
        soul_update_disabled=_env_disabled("INTY_V2_PROTO_SOUL_UPDATE_DISABLED"),
        soul_require_fundamental_signal=_soul_fundamental_signal_gate_enabled(),
    )


_MODEL_ROLE_TO_FN = {
    "memory": memory_model,
    "day_summary": day_summary_model,
    "user": user_model,
    "soul": soul_model,
}


def _make_complete_fn(ws_label: str) -> callable:
    """Build a complete_fn matching kernel signature: (messages, model_role) -> str."""

    def _complete_fn(messages: list[dict[str, Any]], model_role: str) -> str:
        model_fn = _MODEL_ROLE_TO_FN.get(model_role)
        model = model_fn() if model_fn is not None else memory_model()
        return complete(
            messages,
            model=model,
            trace_where=f"memory.{model_role}",
            ws_label=ws_label,
            trace_day=local_date_str(),
        )

    return _complete_fn


def memory_update_after_turn(
    paths: WorkspacePaths,
    *,
    user_text: str,
    assistant_text: str,
) -> None:
    store = get_memory_store(paths.root)
    config = _build_config()
    complete_fn = _make_complete_fn(paths.root.name)
    _kernel_memory_update(
        paths,
        store,
        user_text,
        assistant_text,
        complete_fn,
        config,
    )


def schedule_memory_update_after_turn(
    paths: WorkspacePaths,
    *,
    user_text: str,
    assistant_text: str,
) -> None:
    store = get_memory_store(paths.root)
    config = _build_config()
    complete_fn = _make_complete_fn(paths.root.name)
    _kernel_schedule_memory_update(
        paths,
        store,
        user_text,
        assistant_text,
        complete_fn,
        config,
    )
