"""OpenAI-style system slices from ImplicitSignalBundle.

User sign-on greeting uses ``USER_SIGNED_ON_TRIGGER_SYSTEM_TEXT`` appended **after**
transcript in ``turn.run_turn``, not mixed into the early system prefix (so it stays
the last model-visible instruction before the assistant reply).
"""

from __future__ import annotations

from typing import Any

from app.core.user_time_context_prompt import build_user_time_context_markdown
from app.schemas.implicit_signals import ImplicitSignalBundle

USER_SIGNED_ON_TRIGGER_SYSTEM_TEXT = (
    "## Implicit user signed on signal\n"
    "The user has just come online in the chat session.\n"
    "Respond with a brief, natural, warm greeting or acknowledgment that fits your "
    "character and the relationship."
)

MEMORY_DIARY_USER_LINE_FOR_IMPLICIT_SIGN_ON = "（用户上线：隐式客户端信号）"


def implicit_signal_system_messages(
    bundle: ImplicitSignalBundle | None,
) -> list[dict[str, Any]]:
    """Return early-prefix system dicts (client time only). Sign-on is tail-appended in run_turn."""
    if bundle is None:
        return []
    out: list[dict[str, Any]] = []
    text = build_user_time_context_markdown(
        bundle.client_time.model_dump(exclude_none=True) if bundle.client_time else None
    )
    if text:
        out.append({"role": "system", "content": text})
    return out
