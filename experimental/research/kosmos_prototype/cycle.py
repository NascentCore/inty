"""Discovery campaign loop and report synthesis."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from agents import analysis_stub, literature_stub
from models import CampaignInput, CycleRecord
from planner import PlannerInput, SUMMARY_MAX_CHARS, plan_tasks
from world_model import WorldModelStore

MAX_CYCLES = 3
OBJECTIVE_TEXT = (
    "Identify metabolic changes that explain hypothermic neuroprotection; "
    "prioritize nucleotide-related mechanisms."
)


@dataclass(frozen=True)
class CampaignResult:
    """Artifacts produced by a full campaign run."""

    run_id: str
    run_dir: Path
    world_model: WorldModelStore
    cycle_records: list[CycleRecord]
    report_path: Path


def run_campaign(
    campaign_input: CampaignInput,
    use_world_model: bool,
    cycles: int,
    output_root: Path,
) -> CampaignResult:
    """Execute a minimal Kosmos-style discovery campaign."""
    assert cycles > 0
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    world_model = WorldModelStore.seed()
    last_summary = ""
    cycle_records: list[CycleRecord] = []

    for cycle_index in range(cycles):
        task_batch = plan_tasks(
            PlannerInput(
                use_world_model=use_world_model,
                world_model=world_model,
                last_summary=last_summary,
            )
        )
        if not task_batch.literature_tasks and not task_batch.analysis_tasks:
            break

        cycle_dir = run_dir / f"cycle_{cycle_index}"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        literature_outputs = [
            literature_stub(task, Path(campaign_input.snippets_path))
            for task in task_batch.literature_tasks
        ]
        analysis_outputs = [
            analysis_stub(
                task,
                Path(campaign_input.dataset_path),
                cycle_dir,
            )
            for task in task_batch.analysis_tasks
        ]

        if use_world_model:
            for output in literature_outputs:
                world_model.ingest_literature_output(output)
            for output in analysis_outputs:
                world_model.ingest_analysis_output(output)
        else:
            for output in literature_outputs + analysis_outputs:
                world_model.completed_task_ids.add(output.task_id)

        last_summary = world_model.render_summary(SUMMARY_MAX_CHARS)
        snapshot = world_model.snapshot()
        world_model.save_snapshot(cycle_dir / "world_model.json")
        (cycle_dir / "literature_outputs.json").write_text(
            json.dumps([output.model_dump() for output in literature_outputs], indent=2),
            encoding="utf-8",
        )
        (cycle_dir / "analysis_outputs.json").write_text(
            json.dumps([output.model_dump() for output in analysis_outputs], indent=2),
            encoding="utf-8",
        )

        cycle_record = CycleRecord(
            cycle_index=cycle_index,
            task_batch=task_batch,
            literature_outputs=literature_outputs,
            analysis_outputs=analysis_outputs,
            world_model_snapshot=snapshot,
        )
        cycle_records.append(cycle_record)
        print(json.dumps({"cycle": cycle_index, "snapshot": snapshot}, indent=2))

    report_path = _write_report(run_dir, world_model, use_world_model)
    manifest = {
        "run_id": run_id,
        "objective": campaign_input.objective,
        "use_world_model": use_world_model,
        "cycles_executed": len(cycle_records),
        "completed_task_ids": sorted(world_model.completed_task_ids),
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return CampaignResult(
        run_id=run_id,
        run_dir=run_dir,
        world_model=world_model,
        cycle_records=cycle_records,
        report_path=report_path,
    )


def _write_report(run_dir: Path, world_model: WorldModelStore, use_world_model: bool) -> Path:
    """Materialize markdown report with claim-to-evidence links."""
    claims = world_model.build_claims()
    lines = [
        "# Kosmos Prototype Discovery Report",
        "",
        f"- mode: {'kosmos_wm' if use_world_model else 'no_world_model'}",
        f"- objective: {OBJECTIVE_TEXT}",
        "",
        "## Claims",
        "",
    ]
    if claims:
        for claim in claims:
            evidence_links = ", ".join(claim.evidence_ids)
            lines.append(f"- [{claim.claim_id}] {claim.text} → evidence: {evidence_links}")
    else:
        lines.append("- No supported claims were produced.")
    lines.extend(["", "## World Model Snapshot", "", "```json"])
    lines.append(json.dumps(world_model.snapshot(), indent=2))
    lines.append("```")
    report_path = run_dir / "report.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path
