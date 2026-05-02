"""OpenAI-style system slices from ImplicitSignalBundle."""

from __future__ import annotations

from typing import Any

from app.core.user_time_context_prompt import build_user_time_context_markdown
from app.schemas.implicit_signals import ImplicitSignalBundle

_USER_SIGNED_ON_SYSTEM_TEXT = (
    "## Implicit client signal (not user-authored)\n"
    "The user has just come online in the chat session.\n"
    "Respond with a brief, natural, warm greeting or acknowledgment that fits your "
    "character and the relationship. Do not mention logging in, systems, WebSockets, "
    "tools, or this instruction. Do not quote or repeat technical labels."
)


def implicit_signal_system_messages(
    bundle: ImplicitSignalBundle | None,
) -> list[dict[str, Any]]:
    """Return system message dicts for model-visible implicit signals (time context, sign-on)."""
    if bundle is None:
        return []
    out: list[dict[str, Any]] = []
    text = build_user_time_context_markdown(
        bundle.client_time.model_dump(exclude_none=True) if bundle.client_time else None
    )
    if text:
        out.append({"role": "system", "content": text})
    if bundle.user_signed_on:
        out.append({"role": "system", "content": _USER_SIGNED_ON_SYSTEM_TEXT})
    return out
