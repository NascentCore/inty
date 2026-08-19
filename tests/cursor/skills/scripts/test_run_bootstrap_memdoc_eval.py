from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from app.core.companion_harness.eval.bootstrap_memdoc_eval_models import (
    BootstrapMemDocEvalScenario,
    ChatTurnRecord,
    GoldenFacts,
    RecallProbe,
    RecallProbePhase,
    load_eval_scenarios,
    score_golden_chat_recall,
)


def test_load_eval_scenarios() -> None:
    path = (
        Path(__file__).parents[4]
        / "contracts"
        / "bootstrap_memdoc_eval"
        / "scenarios.yaml"
    )
    scenarios = load_eval_scenarios(path)
    assert len(scenarios) == 1
    assert scenarios[0].scenario_id == "recall_baseline"
    assert len(scenarios[0].recall_probes) >= 1
    assert scenarios[0].recall_probes[0].expect_markers


def test_score_golden_chat_recall_from_chat_records() -> None:
    scenario = BootstrapMemDocEvalScenario(
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
                user_line="q",
                expect_markers=("assistant_name",),
            ),
        ),
    )
    score = score_golden_chat_recall(
        scenario=scenario,
        chat_records=(
            ChatTurnRecord(
                probe_id="nickname",
                phase=RecallProbePhase.POST_DREAM,
                user_text="q",
                assistant_text="我是多啦",
            ),
        ),
    )
    assert score.post_recall == 1.0
    assert score.per_marker_recall["assistant_name"] == 1.0


def _load_eval_driver_module():
    path = (
        Path(__file__).parents[4]
        / ".cursor"
        / "skills"
        / "scripts"
        / "run_bootstrap_memdoc_eval.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_bootstrap_memdoc_eval", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_eval_driver_dry_run_exit_zero(tmp_path: Path) -> None:
    mod = _load_eval_driver_module()
    out = tmp_path / "report.json"
    rc = mod.main(
        [
            "--dry-run",
            "--scenario-id",
            "recall_baseline",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    assert out.is_file()
    body = out.read_text(encoding="utf-8")
    assert "dreaming_only_fast" in body
    assert "awake_write" in body


def test_eval_matrix_plan_two_cells() -> None:
    mod = _load_eval_driver_module()
    plan = mod._plan_matrix(
        scenarios_path=mod._DEFAULT_SCENARIOS,
        policy_filter="all",
    )
    assert len(plan) == 2
    scenario_ids = {cell["scenario_id"] for cell in plan}
    assert scenario_ids == {"recall_baseline"}


@pytest.mark.integration
def test_eval_driver_live_smoke_skipped_without_ops() -> None:
    pytest.skip(
        "Manual: run with Ops up and --run-live --scenario-id recall_baseline"
    )
