"""Prompt copy and early-prefix slices from ImplicitSignalBundle.

Sign-on greeting uses ``USER_SIGNED_ON_TRIGGER_USER_TEXT`` appended **after** the
loaded transcript in ``turn.run_turn`` as a **user** message, not mixed into the early
system prefix. A tail **system** line for the same text was observed to yield overly
similar greetings across turns (models weigh trailing system instructions heavily);
framing the trigger as user input improves variation while keeping the signal last in
the dialogue before the assistant reply. The Chinese bootstrap line mirrors the old
WebSocket connect-time interactive kickoff placeholder so USER_INTERACTIVE sessions
still open naturally when the client triggers implicit greeting via ``user_signed_on`` (+ ``implicit_greeting``).

Client wall-clock context (``ImplicitSignalBundle.client_time``) is not injected here;
``turn_pipeline`` appends factual ``user-time:`` lines to the tail **user** message for
the LLM when the feature flag is enabled.
"""

from __future__ import annotations

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
