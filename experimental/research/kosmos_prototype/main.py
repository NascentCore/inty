#!/usr/bin/env python3
"""Kosmos minimal prototype — structured world model discovery loop."""

from __future__ import annotations

from pathlib import Path

import cyclopts

from cycle import MAX_CYCLES, OBJECTIVE_TEXT, run_campaign
from models import CampaignInput

app = cyclopts.App(name="kosmos-prototype", help="Minimal Kosmos architecture prototype.")
ROOT = Path(__file__).resolve().parent


@app.command
def run(
    *,
    cycles: int = MAX_CYCLES,
    no_world_model: bool = False,
    dataset: Path = ROOT / "data" / "metabolomics.csv",
    snippets: Path = ROOT / "data" / "paper_snippets.json",
    output_dir: Path = ROOT / "runs",
) -> None:
    """Run a discovery campaign and write report artifacts."""
    campaign_input = CampaignInput(
        objective=OBJECTIVE_TEXT,
        dataset_path=str(dataset),
        snippets_path=str(snippets),
    )
    result = run_campaign(
        campaign_input=campaign_input,
        use_world_model=not no_world_model,
        cycles=cycles,
        output_root=output_dir,
    )
    print(f"run_id={result.run_id}")
    print(f"report={result.report_path}")


if __name__ == "__main__":
    app()
