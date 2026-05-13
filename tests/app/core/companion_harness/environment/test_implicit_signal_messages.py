"""Implicit signal companion behavior (no user-time system slice)."""

from __future__ import annotations

import pytest

from app.core.companion_harness.environment.implicit_signal_messages import (
    implicit_user_signed_on_chat_turn,
)
from app.core.companion_harness.contracts.models import ContextMeta, PromptBundle
from app.core.companion_harness.system_hierarchy.prompts.system_messages import (
    build_system_messages,
)
from app.core.companion_harness.runtime.turn_pipeline import (
    _companion_tail_user_body_for_llm,
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


def test_companion_tail_user_body_appends_time_lines(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.companion_harness.runtime import turn_pipeline as turn_pipeline_mod

    monkeypatch.setattr(
        turn_pipeline_mod._global_config.app.features,
        "experimental_enable_chat_with_user_time_context",
        True,
    )
    bundle = ImplicitSignalBundle(
        client_time=UserTimeContext(
            local_time="2026-05-01T08:00:00+08:00",
            timezone="Asia/Shanghai",
            utc_offset_minutes=480,
        ),
    )
    out = _companion_tail_user_body_for_llm(
        user_text="hello",
        implicit_sign_on_turn=False,
        implicit_signal_bundle=bundle,
    )
    assert out.startswith("hello\n\n")
    assert "user-time: 2026-05-01T08:00:00+08:00" in out
    assert "user-time-zone: Asia/Shanghai" in out
    assert "user-time-utc-offset: UTC+08:00" in out
