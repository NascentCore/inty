"""Implicit signal slices for companion system messages."""

from __future__ import annotations

from app.core.agentic_kernel.companion.implicit_signal_messages import (
    implicit_signal_system_messages,
)
from app.core.user_time_context_prompt import USER_TIME_CONTEXT_SYSTEM_PROMPT_GUIDANCE
from app.core.agentic_kernel.companion.models import ContextMeta, PromptBundle
from app.core.agentic_kernel.companion.prompts import build_system_messages
from app.schemas.chat import UserTimeContext
from app.schemas.implicit_signals import ImplicitSignalBundle


def test_implicit_signal_system_messages_empty_when_no_client_time() -> None:
    assert implicit_signal_system_messages(None) == []
    assert (
        implicit_signal_system_messages(
            ImplicitSignalBundle(client_time=None, server_received_at_utc=None)
        )
        == []
    )


def test_implicit_signal_system_messages_skips_all_none_user_time_fields() -> None:
    b = ImplicitSignalBundle(client_time=UserTimeContext())
    assert implicit_signal_system_messages(b) == []


def test_implicit_signal_system_messages_user_signed_on_slice() -> None:
    b = ImplicitSignalBundle(user_signed_on=True)
    msgs = implicit_signal_system_messages(b)
    assert len(msgs) == 1
    assert msgs[0]["role"] == "system"
    assert "come online" in (msgs[0]["content"] or "").lower()


def test_implicit_signal_system_messages_time_and_sign_on_both() -> None:
    b = ImplicitSignalBundle(
        client_time=UserTimeContext(local_time="2026-05-01T12:00:00Z"),
        user_signed_on=True,
    )
    msgs = implicit_signal_system_messages(b)
    assert len(msgs) == 2
    assert "##User Time Context" in msgs[0]["content"]
    assert "Implicit client signal" in msgs[1]["content"]


def test_implicit_signal_system_messages_includes_title_and_guidance() -> None:
    b = ImplicitSignalBundle(
        client_time=UserTimeContext(
            local_time="2026-05-01T08:00:00+08:00",
            timezone="Asia/Shanghai",
            utc_offset_minutes=480,
        )
    )
    msgs = implicit_signal_system_messages(b)
    assert len(msgs) == 1
    assert msgs[0]["role"] == "system"
    content = msgs[0]["content"]
    assert "##User Time Context" in content
    assert "User local time:" in content
    assert "Asia/Shanghai" in content
    assert "UTC+08:00" in content
    for line in USER_TIME_CONTEXT_SYSTEM_PROMPT_GUIDANCE:
        assert line in content


def test_build_system_messages_inserts_implicit_after_security() -> None:
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
    first_system_contents = [m["content"] for m in msgs if m["role"] == "system"]
    assert "##User Time Context" in "\n".join(first_system_contents)
    sec_idx = next(
        i
        for i, m in enumerate(msgs)
        if m["role"] == "system" and "SOUL 与 USER" in (m.get("content") or "")
    )
    utc_idx = next(
        i
        for i, m in enumerate(msgs)
        if m["role"] == "system" and "##User Time Context" in (m.get("content") or "")
    )
    assert utc_idx > sec_idx
