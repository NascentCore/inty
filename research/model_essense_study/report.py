"""
Markdown report scaffold for model essence study.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .config import ModelEssenseStudyConfig


def build_scaffold_report(
    *,
    config: ModelEssenseStudyConfig,
    analysis_path: Path,
    figures: Iterable[Path],
) -> str:
    analysis_payload: dict = {}
    if analysis_path.exists():
        analysis_payload = json.loads(analysis_path.read_text(encoding="utf-8"))

    lines: list[str] = []
    lines.append("# Model Essence Study — Framework Report")
    lines.append("")
    lines.append(
        f"- Generated at (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}"
    )
    lines.append(f"- Persona target: {config.experiment.persona_count}")
    lines.append(f"- Stimulus target: {config.experiment.stimulus_count}")
    lines.append(f"- Repeats per cell: {config.experiment.repeats_per_cell}")
    lines.append(f"- Models: {', '.join(config.experiment.model_ids)}")
    lines.append("")
    lines.append("## Analysis Snapshot")
    lines.append("")
    if analysis_payload:
        summary = analysis_payload.get("summary", {})
        lines.append(f"- records_total: {summary.get('records_total', 0)}")
        lines.append(f"- records_success: {summary.get('records_success', 0)}")
        lines.append(f"- records_refusal: {summary.get('records_refusal', 0)}")
        lines.append(f"- records_error: {summary.get('records_error', 0)}")
    else:
        lines.append("_No analysis payload found._")
    lines.append("")
    lines.append("## Figure Artifacts")
    lines.append("")
    for fig in figures:
        lines.append(f"- {fig}")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append(
        "- This report summarizes the latest execution artifacts. Final conclusions require full experiment execution."
    )
    lines.append(
        "- Model availability should be checked via `probe-model-availability` before large runs."
    )
    lines.append("")
    return "\n".join(lines)
