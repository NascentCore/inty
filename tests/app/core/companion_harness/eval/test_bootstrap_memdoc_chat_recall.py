"""Tests for Bootstrap MemDoc chat golden-fact recall scoring."""

from __future__ import annotations

from app.core.companion_harness.eval.bootstrap_memdoc_eval_models import (
    BootstrapMemDocEvalScenario,
    ChatTurnRecord,
    GoldenFacts,
    RecallProbe,
    RecallProbePhase,
    score_golden_chat_recall,
)


def _unit_scenario() -> BootstrapMemDocEvalScenario:
    return BootstrapMemDocEvalScenario(
        scenario_id="unit",
        description="unit",
        user_turns=("hi",),
        experience_profile=None,
        golden_facts=GoldenFacts(
            user_address="大雄",
            assistant_name="多啦",
            language="zh",
            relationship_framing="陪",
            session_intent="casual_chat",
        ),
        recall_probes=(
            RecallProbe(
                probe_id="nickname",
                user_line="你还记得我怎么称呼你吗？",
                expect_markers=("assistant_name",),
            ),
            RecallProbe(
                probe_id="user_name",
                user_line="我叫什么？",
                expect_markers=("user_address",),
            ),
        ),
    )


def test_score_golden_chat_recall_post_hits() -> None:
    scenario = _unit_scenario()
    score = score_golden_chat_recall(
        scenario=scenario,
        chat_records=(
            ChatTurnRecord(
                probe_id="nickname",
                phase=RecallProbePhase.POST_DREAM,
                user_text="你还记得我怎么称呼你吗？",
                assistant_text="当然记得，你是多啦的伙伴大雄。",
            ),
            ChatTurnRecord(
                probe_id="user_name",
                phase=RecallProbePhase.POST_DREAM,
                user_text="我叫什么？",
                assistant_text="你叫大雄呀。",
            ),
        ),
    )
    assert score.post_recall == 1.0
    assert score.pre_recall is None
    assert score.overall_recall == 1.0
    assert score.per_marker_recall["assistant_name"] == 1.0
    assert score.per_marker_recall["user_address"] == 1.0


def test_score_golden_chat_recall_pre_vs_post() -> None:
    scenario = _unit_scenario()
    score = score_golden_chat_recall(
        scenario=scenario,
        chat_records=(
            ChatTurnRecord(
                probe_id="nickname",
                phase=RecallProbePhase.PRE_DREAM,
                user_text="你还记得我怎么称呼你吗？",
                assistant_text="我是 Inty，很高兴认识你。",
            ),
            ChatTurnRecord(
                probe_id="nickname",
                phase=RecallProbePhase.POST_DREAM,
                user_text="你还记得我怎么称呼你吗？",
                assistant_text="我是多啦，陪大雄聊天。",
            ),
            ChatTurnRecord(
                probe_id="user_name",
                phase=RecallProbePhase.POST_DREAM,
                user_text="我叫什么？",
                assistant_text="大雄。",
            ),
        ),
    )
    assert score.pre_recall == 0.0
    assert score.post_recall == 1.0
    assert score.overall_recall == 2.0 / 3.0


def test_score_golden_chat_recall_awake_post_docs_phase() -> None:
    scenario = _unit_scenario()
    score = score_golden_chat_recall(
        scenario=scenario,
        chat_records=(
            ChatTurnRecord(
                probe_id="nickname",
                phase=RecallProbePhase.POST_DOCS,
                user_text="q",
                assistant_text="多啦在这。",
            ),
        ),
    )
    assert score.post_recall == 1.0
