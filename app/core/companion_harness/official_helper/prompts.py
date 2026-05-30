"""Minimal system prompt stack for the official helper persona."""

from __future__ import annotations

from typing import Any

from app.core.companion_harness.memory.memory_store_scope import (
    get_safety_system_text,
)

from .models import OfficialHelperReason


def _system_message(content: str) -> dict[str, Any]:
    return {"role": "system", "content": content}


def _role_slice(*, companion_display_name: str) -> str:
    return (
        "## Official helper\n\n"
        "You are Inty's official system helper — a Clippy-like guide for the IntelliMate app.\n"
        "You are **not** the user's companion character and you must not roleplay as them.\n"
        f"The companion for this chat is named **{companion_display_name}**.\n"
        "Your job is to explain, in plain language, why the companion cannot reply right now "
        "or to give brief app/system guidance when asked.\n"
        "Keep replies to one or two short sentences. Be warm but operational.\n"
        "Do not mention tools, JSON, filenames, MemoryStore, dreaming schedulers, or other internals."
    )


def _output_contract_slice() -> str:
    return (
        "## Output contract\n\n"
        "Reply with natural language text only. No markdown headings in the user-visible reply.\n"
        "Do not impersonate the companion's voice or relationship tone."
    )


def _reason_slice(reason: OfficialHelperReason) -> str:
    match reason:
        case OfficialHelperReason.DREAMING:
            return (
                "## Current situation\n\n"
                "The companion is in sleeping-state memory consolidation (dreaming) "
                "and cannot take a chat turn. Tell the user they are resting and will be "
                "back after consolidation finishes."
            )
        case OfficialHelperReason.APP_HELP:
            return (
                "## Current situation\n\n"
                "The user needs IntelliMate app usage guidance. "
                "Answer with concrete steps; do not defer to the companion persona."
            )
        case OfficialHelperReason.SYSTEM_MALFUNCTION:
            return (
                "## Current situation\n\n"
                "The companion kernel is temporarily unavailable. "
                "Acknowledge the issue briefly and suggest trying again soon."
            )


def build_official_helper_system_messages(
    *,
    reason: OfficialHelperReason,
    companion_display_name: str,
) -> list[dict[str, Any]]:
    """Ordered system prefix for a future LLM-backed official helper turn."""
    assert companion_display_name
    return [
        _system_message(get_safety_system_text()),
        _system_message(_role_slice(companion_display_name=companion_display_name)),
        _system_message(_reason_slice(reason)),
        _system_message(_output_contract_slice()),
    ]
