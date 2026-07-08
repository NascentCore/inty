"""Prompt copy and early-prefix slices from ImplicitSignalBundle.

Sign-on greeting uses ``USER_SIGNED_ON_TRIGGER_USER_TEXT`` appended **after** the
loaded transcript in ``turn.run_turn`` as a **user** message, not mixed into the early
system prefix. A tail **system** line for the same text was observed to yield overly
similar greetings across turns (models weigh trailing system instructions heavily);
framing the trigger as user input improves variation while keeping the signal last in
the dialogue before the assistant reply. During interactive bootstrap, ``user_signed_on``
with ``message_id`` is the first-turn opener (replacing the legacy WebSocket kickoff
placeholder); system stack carries ``BOOTSTRAP.md`` via ``prompting/system_messages.py`` bootstrap slices.

Client wall-clock context (``ImplicitSignalBundle.client_time``) is not injected here;
``turn_pipeline`` emits a dedicated ``## user-time-context`` **system** message
(``User's time`` / ``Time zone`` lines) immediately before the tail **user** message when
the feature flag is enabled.
"""

from __future__ import annotations

from app.schemas.implicit_signals import ImplicitSignalBundle

USER_SIGNED_ON_TRIGGER_USER_TEXT = (
    "## Implicit user signed on signal\n"
    "- The user has just come online in the chat session.\n"
    "- If in bootstrap phase, ask one question at a time, proactively drive the relationship-establishment flow;\n"
    "- If not in bootstrap phase, continue the conversation naturally with a warm greeting that fits the current conversation context.\n"
)

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
