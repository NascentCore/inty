"""OpenAI-style system slices from ImplicitSignalBundle."""

from __future__ import annotations

from typing import Any

from app.core.user_time_context_prompt import build_user_time_context_markdown
from app.schemas.implicit_signals import ImplicitSignalBundle


def implicit_signal_system_messages(
    bundle: ImplicitSignalBundle | None,
) -> list[dict[str, Any]]:
    """Return zero or one system message dicts for model-visible implicit signals."""
    if bundle is None:
        return []
    text = build_user_time_context_markdown(
        bundle.client_time.model_dump(exclude_none=True) if bundle.client_time else None
    )
    if not text:
        return []
    return [{"role": "system", "content": text}]
