"""Load OPENAI_API_KEY (and optional OPENROUTER_BASE_URL) from Inty YAML config."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def apply_llm_env_from_config_yaml(config_path: Path) -> dict[str, str]:
    """
    If OPENROUTER_API_KEY / OPENAI_API_KEY are unset, set OPENAI_API_KEY from YAML.

    Resolution order for the key:
    1. Top-level ``openai_api_key`` or ``OPENAI_API_KEY``
    2. ``agent.api_key`` (same field used by backend ``config.yaml``)

    Optional: ``agent.openrouter_base_url`` -> OPENROUTER_BASE_URL when unset.

    Returns a dict of env keys that were set (for logging/tests only).
    """
    path = config_path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"config yaml not found: {path}")

    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: root must be a mapping")

    key = ""
    for k in ("openai_api_key", "OPENAI_API_KEY"):
        v = raw.get(k)
        if isinstance(v, str) and v.strip():
            key = v.strip()
            break

    agent = raw.get("agent")
    if not key and isinstance(agent, dict):
        v = agent.get("api_key")
        if isinstance(v, str) and v.strip():
            key = v.strip()

    applied: dict[str, str] = {}
    if key:
        if not (os.getenv("OPENROUTER_API_KEY") or "").strip() and not (
            os.getenv("OPENAI_API_KEY") or ""
        ).strip():
            os.environ["OPENAI_API_KEY"] = key
            applied["OPENAI_API_KEY"] = "(from yaml)"

    base = ""
    if isinstance(agent, dict):
        for bk in ("openrouter_base_url", "api_base", "openai_api_base"):
            v = agent.get(bk)
            if isinstance(v, str) and v.strip():
                base = v.strip()
                break

    if base and not (os.getenv("OPENROUTER_BASE_URL") or "").strip():
        os.environ["OPENROUTER_BASE_URL"] = base
        applied["OPENROUTER_BASE_URL"] = base

    return applied
