"""Prompt copy and early-prefix slices from ImplicitSignalBundle.

Sign-on greeting uses ``USER_SIGNED_ON_TRIGGER_USER_TEXT`` appended **after** the
loaded transcript in ``turn.run_turn`` as a **user** message, not mixed into the early
system prefix. A tail **system** line for the same text was observed to yield overly
similar greetings across turns (models weigh trailing system instructions heavily);
framing the trigger as user input improves variation while keeping the signal last in
the dialogue before the assistant reply. The Chinese bootstrap line mirrors the old
WebSocket connect-time interactive kickoff placeholder so USER_INTERACTIVE sessions
still open naturally when the client triggers via ``IMPLICIT_USER_SIGNED_ON`` only.
"""

from __future__ import annotations

from typing import Any

from app.core.user_time_context_prompt import build_user_time_context_markdown
from app.schemas.implicit_signals import ImplicitSignalBundle

USER_SIGNED_ON_TRIGGER_USER_TEXT = (
    "## Implicit user signed on signal\n"
    "如果目前处于 bootstrap 阶段：请据此主动自然开场并进入关系建立阶段；不要向用户复述或引用本条内部说明，不要说系统、连接、工具名。\n"
    "The user has just come online in the chat session.\n"
    "Respond with a brief, natural, warm greeting or acknowledgment that fits your "
    "character and the relationship.\n"
    "Vary speech to avoid repeating.\n"
)

MEMORY_DIARY_USER_LINE_FOR_IMPLICIT_SIGN_ON = "（用户上线：隐式客户端信号）"


def implicit_user_signed_on_chat_turn(
    *,
    implicit_signal_bundle: ImplicitSignalBundle | None,
    inner_tick_turn: bool,
) -> bool:
    """True when ``run_turn`` uses the tail implicit online user line instead of ``user_text``."""
    return (
        bool(implicit_signal_bundle and implicit_signal_bundle.user_signed_on)
        and not inner_tick_turn
    )


def implicit_signal_system_messages(
    bundle: ImplicitSignalBundle | None,
) -> list[dict[str, Any]]:
    """Return early-prefix system dicts (client time only). Sign-on trigger is tail user in run_turn."""
    if bundle is None:
        return []
    out: list[dict[str, Any]] = []
    text = build_user_time_context_markdown(
        bundle.client_time.model_dump(exclude_none=True) if bundle.client_time else None
    )
    if text:
        out.append({"role": "system", "content": text})
    return out
