"""Normalize OpenAI Chat Completions ``tools`` payloads before HTTP (strict mode, shallow copies).

Companion builds tool dicts by hand in ``tools.companion_tool_runtime``; this module applies a single
``prepare_openai_tools_for_chat_completions`` pass so new tools cannot omit ``strict`` and gateways
that reject strict JSON-schema tools can be bypassed via ``INTY_OPENAI_TOOLS_STRICT``.
"""

from __future__ import annotations

import os
from typing import Any


def openai_tools_strict_default_from_env() -> bool:
    """Return whether function tools should request OpenAI-style ``strict`` (default True)."""
    raw = os.environ.get("INTY_OPENAI_TOOLS_STRICT")
    if raw is None or not str(raw).strip():
        return True
    s = str(raw).strip().lower()
    if s in ("0", "false", "no", "off", "none"):
        return False
    if s in ("1", "true", "yes", "on"):
        return True
    raise ValueError(
        f"Invalid INTY_OPENAI_TOOLS_STRICT={raw!r}; use 1/true or 0/false, or unset for default (on)"
    )


def openai_function_tool(
    name: str,
    description: str,
    parameters: dict[str, Any],
    *,
    extra_function_keys: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one ``{"type": "function", "function": {...}}`` entry without ``strict`` (prepare adds it)."""
    fn: dict[str, Any] = {
        "name": name,
        "description": description,
        "parameters": parameters,
    }
    if extra_function_keys:
        for k, v in extra_function_keys.items():
            if k in ("name", "description", "parameters", "strict"):
                raise ValueError(
                    f"extra_function_keys must not override reserved key {k!r}"
                )
            fn[k] = v
    return {"type": "function", "function": fn}


def prepare_openai_tools_for_chat_completions(
    tools: list[dict[str, Any]],
    *,
    strict: bool | None = None,
) -> list[dict[str, Any]]:
    """
    Return a new tool list with shallow-copied entries; each ``function`` object gets ``strict``
    set from ``strict`` or ``INTY_OPENAI_TOOLS_STRICT`` (when ``strict`` is None).

    Aligns with OpenAI Python SDK expectations for structured parsing of tool calls.
    Does not mutate the input list or original dicts.
    """
    effective_strict = (
        openai_tools_strict_default_from_env() if strict is None else strict
    )
    out: list[dict[str, Any]] = []
    for item in tools:
        if not isinstance(item, dict):
            out.append(item)
            continue
        tool = dict(item)
        if tool.get("type") != "function":
            out.append(tool)
            continue
        fn = tool.get("function")
        if not isinstance(fn, dict):
            out.append(tool)
            continue
        fn_copy = dict(fn)
        if effective_strict:
            fn_copy["strict"] = True
        else:
            fn_copy["strict"] = False
        tool["function"] = fn_copy
        out.append(tool)
    return out
