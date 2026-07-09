from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from app.core.companion_harness.companion.bootstrap_memdoc_policy import (
    BootstrapMemDocPolicy,
)
from app.core.companion_harness.eval.bootstrap_memdoc_eval_models import (
    BootstrapMemDocCheckpoint,
    BootstrapMemDocEvalScenario,
    BootstrapMemDocSnapshot,
    GoldenFacts,
    MemDocSnapshotBody,
    load_eval_scenarios,
    score_bootstrap_memdoc_run,
)


def test_load_eval_scenarios() -> None:
    path = (
        Path(__file__).parents[4]
        / "contracts"
        / "bootstrap_memdoc_eval"
        / "scenarios.yaml"
    )
    scenarios = load_eval_scenarios(path)
    assert len(scenarios) >= 6
    assert scenarios[0].scenario_id == "standard_zh_nickname"


def test_score_bootstrap_memdoc_run_recall_from_t1() -> None:
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
        settled_turns=("hey",),
    )
    t1 = BootstrapMemDocSnapshot(
        checkpoint=BootstrapMemDocCheckpoint.T1_FIRST_DREAM,
        memdocs=(
            MemDocSnapshotBody(
                relative_path="IDENTITY.md",
                sequence_id=2,
                body_preview="我是多啦，陪大雄聊天",
                contains_markers={"assistant_name": True},
            ),
        ),
        prompt_markers={"assistant_name": True},
        settled_reply_preview="",
        tool_background_counts={},
    )
    scores = score_bootstrap_memdoc_run(
        scenario=scenario,
        policy_value=BootstrapMemDocPolicy.DREAMING_INCEPTION.value,
        snapshots={BootstrapMemDocCheckpoint.T1_FIRST_DREAM: t1},
        memory_seed_preview="MEMORY seed",
        soul_seed_preview="SOUL seed",
        bootstrap_complete_at=0.0,
        dreaming_checkpoint_at=12.5,
    )
    assert scores.seconds_to_t1 == 12.5
    assert scores.golden_field_recall["IDENTITY.md"] > 0.0


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
            "standard_zh_nickname",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    assert out.is_file()


@pytest.mark.integration
def test_eval_driver_live_smoke_skipped_without_ops() -> None:
    pytest.skip(
        "Manual: run with Ops up and --run-live --scenario-id standard_zh_nickname"
    )
