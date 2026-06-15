"""When IM channel transport should send ``handle_user_text`` return text.

Generated entirely by Cursor agent.
"""


def agentic_loop_suppresses_transport_reply(
    *,
    agentic_loop_channel_wired: bool,
    interactive_bootstrap_active: bool,
    assistant_reply: str,
) -> bool:
    """True when per-call loop downlink already delivered the visible user-chat reply.

    Bootstrap agentic loop uses ``defer_terminal_user_reply``; the terminal reply still
    goes through transport (Telegram ``sendMessage`` / Hermes handler return).
    Settled user-chat streams foreground via ``agentic_loop_channel`` — transport must
    not send the same assistant text again.
    """
    reply = assistant_reply.strip()
    return bool(
        agentic_loop_channel_wired and reply and not interactive_bootstrap_active
    )
