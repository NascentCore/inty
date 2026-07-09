#!/usr/bin/env python3
"""L1 Bootstrap MemDoc policy eval driver (#3606).

Report-only: always exit 0. Does not gate CI. Requires Ops restarted with
``INTY_CONFIG_YAML=devops/config.yaml.bootstrap_memdoc_eval.yaml`` and matching
``bootstrap_memdoc_policy`` per matrix cell.

Generated entirely by Cursor agent for Bootstrap MemDoc eval slice.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_SCENARIOS = (
    _REPO_ROOT / "contracts" / "bootstrap_memdoc_eval" / "scenarios.yaml"
)
_DEFAULT_CONFIG = _REPO_ROOT / "devops" / "config.yaml.bootstrap_memdoc_eval.yaml"
_TAG = "[bootstrap-memdoc-eval]"

_POLICIES: tuple[str, ...] = (
    "awake_write",
    "dreaming_only",
    "dreaming_inception",
)

_MATRIX_CELLS: tuple[tuple[str, int], ...] = (
    ("awake_write", 10),
    ("dreaming_only", 10),
    ("dreaming_only", 7200),
    ("dreaming_inception", 10),
)


def _ensure_import_path(repo_root: Path) -> None:
    root = str(repo_root)
    if root not in sys.path:
        sys.path.insert(0, root)


def _load_scenarios(path: Path) -> tuple[Any, ...]:
    _ensure_import_path(_REPO_ROOT)
    from app.core.companion_harness.eval.bootstrap_memdoc_eval_models import (
        load_eval_scenarios,
    )

    return load_eval_scenarios(path)


def _plan_matrix(
    *,
    scenarios_path: Path,
    policy_filter: str,
) -> list[dict[str, Any]]:
    scenarios = _load_scenarios(scenarios_path)
    plan: list[dict[str, Any]] = []
    for scenario in scenarios:
        for matrix_policy, idle in _MATRIX_CELLS:
            if policy_filter != "all" and policy_filter != matrix_policy:
                continue
            label = matrix_policy
            if matrix_policy == "dreaming_only":
                label = "dreaming_only_prod" if idle == 7200 else "dreaming_only_fast"
            plan.append(
                {
                    "scenario_id": scenario.scenario_id,
                    "policy": matrix_policy,
                    "dreaming_idle_seconds": idle,
                    "label": label,
                }
            )
    return plan


def _write_report(
    *,
    output: Path,
    cells: list[dict[str, Any]],
    stderr: TextIO,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "cells": cells,
        "note": (
            "L1 report-only eval (#3606). Restart Ops with matching "
            "bootstrap_memdoc_policy before each live cell."
        ),
    }
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"{_TAG} wrote {output}", file=stderr)


def _run_live_cell(
    *,
    repo_root: Path,
    config_path: Path,
    scenario_id: str,
    policy: str,
    dreaming_idle_seconds: int,
    dreaming_wait_sec: float,
    stderr: TextIO,
) -> dict[str, Any]:
    """Run one eval cell via REPL regression helpers when Ops is up."""

    _ensure_import_path(repo_root)
    scenarios = _load_scenarios(_DEFAULT_SCENARIOS)
    scenario = next(
        (s for s in scenarios if s.scenario_id == scenario_id),
        None,
    )
    if scenario is None:
        raise ValueError(f"unknown scenario_id: {scenario_id!r}")

    print(
        f"{_TAG} LIVE cell scenario={scenario_id} policy={policy} "
        f"idle={dreaming_idle_seconds}s — ensure Ops uses "
        f"INTY_CONFIG_YAML={config_path} and bootstrap_memdoc_policy={policy}",
        file=stderr,
        flush=True,
    )

    from app.core.companion_harness.eval.bootstrap_memdoc_eval_models import (
        BootstrapMemDocCheckpoint,
        BootstrapMemDocSnapshot,
        MemDocSnapshotBody,
        score_bootstrap_memdoc_run,
    )
    from app.core.companion_harness.memory.memory_store_scope import (
        load_template_seed_text,
    )

    regression_path = (
        repo_root / ".cursor" / "skills" / "scripts" / "run_inty_repl_regression.py"
    )
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_inty_repl_regression", regression_path
    )
    assert spec is not None and spec.loader is not None
    reg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reg)

    agent_id = reg._create_agent_id(
        repo_root=repo_root,
        api_base=reg._default_api_base(repo_root),
        token_path=str(repo_root / ".secrets" / "repl-regression-token.json"),
        http_timeout=60.0,
        stderr=stderr,
    )
    user_id = reg._resolve_regression_user_id(repo_root, config_path)

    t0 = time.monotonic()
    snapshots: dict[BootstrapMemDocCheckpoint, BootstrapMemDocSnapshot] = {}
    snapshots[BootstrapMemDocCheckpoint.T0_COMPLETE] = BootstrapMemDocSnapshot(
        checkpoint=BootstrapMemDocCheckpoint.T0_COMPLETE,
        memdocs=(),
        prompt_markers={},
        settled_reply_preview="",
        tool_background_counts={},
    )

    dreaming_result = reg._wait_dreaming_consolidation(
        repo_root,
        config_path,
        user_id=user_id,
        agent_id=agent_id,
        memory_sequence_before=0,
        wait_sec=dreaming_wait_sec,
        stderr=stderr,
        skip_db_checks=False,
    )
    t1 = time.monotonic()

    scores = score_bootstrap_memdoc_run(
        scenario=scenario,
        policy_value=policy,
        snapshots=snapshots,
        memory_seed_preview=load_template_seed_text("MEMORY.md")[:200],
        soul_seed_preview=load_template_seed_text("SOUL.md")[:200],
        bootstrap_complete_at=t0,
        dreaming_checkpoint_at=t1 if dreaming_result.checkpoint_present else None,
    )

    return {
        "scenario_id": scenario_id,
        "policy": policy,
        "dreaming_idle_seconds": dreaming_idle_seconds,
        "agent_id": agent_id,
        "dreaming_checkpoint_present": dreaming_result.checkpoint_present,
        "scores": scores.model_dump(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bootstrap MemDoc L1 eval")
    parser.add_argument(
        "--scenarios-yaml",
        type=Path,
        default=_DEFAULT_SCENARIOS,
    )
    parser.add_argument(
        "--config-yaml",
        type=Path,
        default=_DEFAULT_CONFIG,
    )
    parser.add_argument(
        "--policy",
        choices=[*_POLICIES, "all"],
        default="all",
    )
    parser.add_argument("--scenario-id", default="")
    parser.add_argument("--all-scenarios", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--dreaming-wait-sec", type=float, default=45.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tmp")
        / f"bootstrap-memdoc-eval-{int(time.time())}.json",
    )
    args = parser.parse_args(argv)

    stderr = sys.stderr
    policies: tuple[str, ...]
    if args.policy == "all":
        policies = _POLICIES
    else:
        policies = (args.policy,)

    plan = _plan_matrix(
        scenarios_path=args.scenarios_yaml,
        policy_filter=args.policy,
    )
    if args.scenario_id:
        plan = [c for c in plan if c["scenario_id"] == args.scenario_id]
    if not args.all_scenarios and not args.scenario_id and args.dry_run:
        pass

    if args.dry_run:
        print(f"{_TAG} matrix plan ({len(plan)} cells):", file=stderr)
        for cell in plan:
            print(
                f"  {cell['scenario_id']} × {cell['label']} "
                f"(idle={cell['dreaming_idle_seconds']}s)",
                file=stderr,
            )
        _write_report(output=args.output, cells=plan, stderr=stderr)
        return 0

    cells: list[dict[str, Any]] = []
    if args.run_live:
        for cell in plan:
            try:
                cells.append(
                    _run_live_cell(
                        repo_root=_REPO_ROOT,
                        config_path=args.config_yaml,
                        scenario_id=cell["scenario_id"],
                        policy=cell["policy"],
                        dreaming_idle_seconds=cell["dreaming_idle_seconds"],
                        dreaming_wait_sec=args.dreaming_wait_sec,
                        stderr=stderr,
                    )
                )
            except Exception as exc:
                cells.append({**cell, "error": repr(exc)})
    else:
        cells = plan
        print(
            f"{_TAG} no --run-live: wrote plan only. Use --dry-run or --run-live.",
            file=stderr,
        )

    _write_report(output=args.output, cells=cells, stderr=stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
