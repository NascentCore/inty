"""Unit tests for UserAgent prompt construction."""

from __future__ import annotations

from tools.inty_user_sim.types import (
    AttachmentStyle,
    DisclosurePace,
    GrillObjective,
    GrillSensitivity,
    UserPersona,
)
from tools.inty_user_sim.user_agent import build_user_agent_messages


def _persona() -> UserPersona:
    return UserPersona(
        display_name="阿宁",
        assistant_name="小伴",
        language="zh",
        attachment_style=AttachmentStyle.SECURE,
        disclosure_pace=DisclosurePace.MEDIUM,
        grill_sensitivity=GrillSensitivity.STANDARD,
        backstory_seed="在上海工作",
        relationship_preference="emotional_companion",
    )


def test_build_messages_include_objective() -> None:
    messages = build_user_agent_messages(
        _persona(),
        GrillObjective.RUPTURE,
        [("user", "你好"), ("assistant", "嗨")],
        "嗨",
    )
    assert messages[0]["role"] == "system"
    assert "rupture" in messages[-1]["content"]
    assert "阿宁" in messages[0]["content"]


def test_wait_proactive_instruction() -> None:
    from tools.inty_user_sim.user_agent import _objective_instruction

    text = _objective_instruction(GrillObjective.WAIT_PROACTIVE, _persona())
    assert "Do not send" in text
