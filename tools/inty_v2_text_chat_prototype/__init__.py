"""Legacy import path ``inty_v2_text_chat_prototype`` maps to ``tools.inty_v2_repl``."""

from __future__ import annotations

import importlib
import sys

_SHIM_SUBMODULES = (
    "orchestrator",
    "models",
    "client",
    "paths",
    "workspace_init_tools",
    "memory_store_registry",
    "memory_update",
    "bootstrap",
    "llm_trace",
    "prompts",
    "tool_background",
    "image_gate",
    "fal_z_image_tool",
    "schedule_queue",
    "jsonl_db_store",
    "workspace_init_loop",
)

for _name in _SHIM_SUBMODULES:
    _key = f"{__name__}.{_name}"
    if _key not in sys.modules:
        sys.modules[_key] = importlib.import_module(f"tools.inty_v2_repl.{_name}")
