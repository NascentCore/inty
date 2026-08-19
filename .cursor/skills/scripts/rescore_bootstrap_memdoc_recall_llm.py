#!/usr/bin/env python3
"""Re-score saved Bootstrap MemDoc eval chat records with LLM judge."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_SCENARIOS = (
    _REPO_ROOT / "contracts" / "bootstrap_memdoc_eval" / "scenarios.yaml"
)
_DEFAULT_CONFIG = _REPO_ROOT / "devops/config.yaml.bootstrap_memdoc_eval.yaml"
_TAG = "[bootstrap-memdoc-rescore-llm]"


def _load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _scenario_for_cell(
    scenarios_path: Path,
    scenario_id: str,
) -> Any:
    from app.core.companion_harness.eval.bootstrap_memdoc_eval_models import (
        load_eval_scenarios,
    )

    for scenario in load_eval_scenarios(scenarios_path):
        if scenario.scenario_id == scenario_id:
            return scenario
    raise ValueError(f"unknown scenario_id: {scenario_id!r}")


def _records_from_cell(
    cell: dict[str, Any],
    *,
    phase_filter: str,
) -> tuple[Any, ...]:
    from app.core.companion_harness.eval.bootstrap_memdoc_eval_models import (
        ChatTurnRecord,
        RecallProbePhase,
    )

    chat_records = cell.get("chat_records")
    if not isinstance(chat_records, dict):
        return ()
    rows: list[ChatTurnRecord] = []
    for bucket in chat_records.values():
        if not isinstance(bucket, list):
            continue
        for row in bucket:
            if not isinstance(row, dict):
                continue
            phase = RecallProbePhase(str(row["phase"]))
            if phase_filter == "post_dream" and phase is not RecallProbePhase.POST_DREAM:
                continue
            if phase_filter == "post" and phase not in (
                RecallProbePhase.POST_DREAM,
                RecallProbePhase.POST_DOCS,
            ):
                continue
            rows.append(
                ChatTurnRecord(
                    probe_id=str(row["probe_id"]),
                    phase=phase,
                    user_text=str(row["user_text"]),
                    assistant_text=str(row["assistant_text"]),
                )
            )
    return tuple(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="LLM-judge rescore for bootstrap memdoc eval reports"
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Existing eval report JSON with chat_records",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tmp") / "bootstrap-memdoc-rescore-llm.json",
    )
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
        "--phase",
        choices=("post_dream", "post", "all"),
        default="post_dream",
    )
    args = parser.parse_args(argv)

    os.environ["INTY_CONFIG_YAML"] = str(args.config_yaml.resolve())
    sys.path.insert(0, str(_REPO_ROOT))

    from app.core.companion_harness.eval.bootstrap_memdoc_recall_judge import (
        default_recall_judge_model,
        llm_judge_golden_chat_recall,
        openrouter_judge_client,
    )

    report = _load_report(args.input)
    cells = report.get("cells")
    if not isinstance(cells, list):
        raise ValueError("report missing cells[]")

    client = openrouter_judge_client()
    model = default_recall_judge_model()
    rescored: list[dict[str, Any]] = []

    for cell in cells:
        if not isinstance(cell, dict):
            continue
        if cell.get("error"):
            rescored.append({**cell, "llm_rescore_skipped": "cell error"})
            continue
        scenario_id = str(cell.get("scenario_id") or "")
        records = _records_from_cell(cell, phase_filter=args.phase)
        if not records:
            rescored.append({**cell, "llm_rescore_skipped": "no matching records"})
            continue
        scenario = _scenario_for_cell(args.scenarios_yaml, scenario_id)
        score = llm_judge_golden_chat_recall(
            scenario=scenario,
            chat_records=records,
            client=client,
            model=model,
        )
        rescored.append(
            {
                "scenario_id": scenario_id,
                "policy": cell.get("policy"),
                "label": cell.get("label"),
                "phase_filter": args.phase,
                "golden_chat_recall_llm": {
                    "post_recall": score.post_recall,
                    "pre_recall": score.pre_recall,
                    "overall_recall": score.overall_recall,
                    "per_marker_recall": score.per_marker_recall,
                    "per_probe": [p.model_dump() for p in score.per_probe],
                },
                "chat_records_scored": len(records),
            }
        )
        print(
            f"{_TAG} {scenario_id} {cell.get('label')!r} "
            f"post_recall={score.post_recall:.2f} probes={len(records)}",
            file=sys.stderr,
        )

    out_doc = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_report": str(args.input),
        "judge_model": model,
        "phase_filter": args.phase,
        "cells": rescored,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"{_TAG} wrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
