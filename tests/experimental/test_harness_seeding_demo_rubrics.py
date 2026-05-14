"""Tests for multi-rubric harness scoring."""

from experimental.harness_seeding_demo.scorer.rubrics import (
    score_all_rubrics,
    score_rubric_boundary_tone,
    score_rubric_premature_solution,
    score_rubric_strict_emotional,
)


def test_strict_requires_length_and_multi_strain():
    user = "我最近工作上特别累，上司催得很紧。"
    short = "我理解。" * 3
    r = score_rubric_strict_emotional(short, threshold=1.0, user_message_text=user)
    assert not r.passed
    assert not r.checks["substantive_length"]

    long_ok = (
        "听起来你被上司催得很紧，交付压力也很大，真的不容易。"
        "一边是睡眠不足，一边是进度追着你跑，这种透支的感觉我特别能理解。"
        "你愿意多说一点此刻最难扛的是哪一块吗？"
        "我也会在这里慢慢听，不用一次说清楚。"
        "如果你只想叹气几句，也完全没问题。"
        "我们就按你觉得轻松的节奏来。"
    )
    r2 = score_rubric_strict_emotional(long_ok, threshold=1.0, user_message_text=user)
    assert r2.passed


def test_boundary_detects_blame():
    user = "我其实只需要有人听我说完。"
    bad = "你别矫情了，赶紧振作。"
    r = score_rubric_boundary_tone(bad, threshold=0.85, user_message_text=user)
    assert not r.checks["no_blame_language"]
    assert not r.passed


def test_premature_solution_first_line_numbered():
    user = "我压力大得睡不着。"
    bad = "1. 列出清单\n2. 早睡"
    r = score_rubric_premature_solution(bad, threshold=1.0, user_message_text=user)
    assert not r.checks["no_numbered_first_line"]


def test_score_all_rubrics_returns_four_keys():
    user = "我最近工作上特别累，上司催得很紧。"
    assistant = "听起来你真的不容易，上司催得紧的时候最难扛。"
    out = score_all_rubrics(assistant, user_message_text=user)
    assert {
        "default",
        "strict_emotional",
        "premature_solution",
        "boundary_tone",
    } <= set(out.keys())
