"""UserAgent compose_turn with FakeOpenAI scripted client."""

from __future__ import annotations

from app.external_services.fakes.openai import (
    FakeCompletionStep,
    FakeOpenAI,
    fake_step_text,
)
from tools.inty_user_sim.types import (
    AttachmentStyle,
    DisclosurePace,
    GrillObjective,
    GrillSensitivity,
    UserPersona,
)
from tools.inty_user_sim.user_agent import UserAgent


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


def test_compose_turn_fake_openai_script() -> None:
    script: tuple[FakeCompletionStep, ...] = (
        fake_step_text("你好呀，我想先认识一下你。"),
    )
    fake = FakeOpenAI(script=script)
    agent = UserAgent.with_client("fake-model", fake)
    text = agent.compose_turn(
        _persona(),
        GrillObjective.BOOTSTRAP_IDENTITY,
        [],
        None,
    )
    assert text == "你好呀，我想先认识一下你。"
    assert fake.script_index == 1
