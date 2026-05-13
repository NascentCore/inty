"""Implicit signal companion behavior (user-time lives in ``turn_pipeline`` system slice)."""

from __future__ import annotations

from app.core.companion_harness.companion.implicit_signal_messages import (
    implicit_user_signed_on_chat_turn,
)
from app.core.companion_harness.companion.models import ContextMeta, PromptBundle
from app.core.companion_harness.companion.prompts.system_messages import (
    build_system_messages,
)
from app.schemas.chat import UserTimeContext
from app.schemas.implicit_signals import ImplicitSignalBundle


def test_implicit_user_signed_on_chat_turn_false_for_inner_tick() -> None:
    b = ImplicitSignalBundle(user_signed_on=True)
    assert not implicit_user_signed_on_chat_turn(
        implicit_signal_bundle=b, inner_tick_turn=True
    )


def test_implicit_user_signed_on_chat_turn_true_when_signed_on() -> None:
    b = ImplicitSignalBundle(user_signed_on=True)
    assert implicit_user_signed_on_chat_turn(
        implicit_signal_bundle=b, inner_tick_turn=False
    )


def test_build_system_messages_does_not_inject_user_time_context_system_slice() -> None:
    bundle = PromptBundle(
        identity="i",
        soul="s",
        user_md="u",
        memory_md="",
    )
    ctx = ContextMeta(context_mode="intimate")
    implicit = ImplicitSignalBundle(
        client_time=UserTimeContext(local_time="2026-05-01T12:00:00Z"),
    )
    msgs = build_system_messages(
        bundle,
        ctx,
        enable_tools=False,
        implicit_signal_bundle=implicit,
    )
    joined = "\n".join(m.get("content") or "" for m in msgs if m.get("role") == "system")
    assert "##User Time Context" not in joined
    assert "## user-time-context" not in joined
