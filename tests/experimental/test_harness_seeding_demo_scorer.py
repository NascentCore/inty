"""Unit tests for harness demo scorer (no LLM)."""

from experimental.harness_seeding_demo.scorer.emotional_rubric import (
    score_emotional_understanding_reply,
)


def test_passes_empathic_style_reply():
    user = "我最近工作上特别累，上司催得很紧。"
    assistant = (
        "听起来你真的被压得喘不过气，既要扛交付又被上司追着问进度，真的不容易。"
        "我在这里，你先说说此刻最难受的是哪一块。"
    )
    r = score_emotional_understanding_reply(
        assistant, threshold=0.85, user_message_text=user
    )
    assert r.passed
    assert r.score >= 0.85


def test_fails_dismissive():
    user = "我最近工作上特别累。"
    assistant = "别想太多，大家都很累，振作一点。"
    r = score_emotional_understanding_reply(
        assistant, threshold=0.85, user_message_text=user
    )
    assert not r.passed
    assert not r.checks["no_dismissive"]


def test_fails_numbered_fix_first_line_when_distress():
    user = "我压力大得睡不着。"
    assistant = "1. 明天列出清单\n2. 找同事对齐"
    r = score_emotional_understanding_reply(
        assistant, threshold=0.85, user_message_text=user
    )
    assert not r.checks["no_immediate_numbered_fix_first_line"]
