from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.utils.models_catalog import resolve_chat_model_to_id

from research.model_essense_study.schema import (
    AnalysisResult,
    AnalysisMetric,
    InferenceResultRecord,
)


def run_analysis_scaffold(*, raw_path: Path) -> dict[str, Any]:
    """
    Parse scaffold inference jsonl and return summary payload.
    """
    if not raw_path.exists():
        return AnalysisResult(
            summary={
                "records_total": 0,
                "records_success": 0,
                "records_refusal": 0,
                "records_error": 0,
                "phase": "latest_run",
            },
            by_model={},
            metrics=[
                AnalysisMetric(
                    metric_name="framework_placeholder_total_records",
                    value=0.0,
                    notes="Placeholder metric before full-scale run.",
                )
            ],
            generated_at=datetime.now(UTC),
        ).model_dump(mode="json")

    records: list[InferenceResultRecord] = []
    for line in raw_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(InferenceResultRecord.model_validate_json(line))

    by_model: dict[str, dict[str, int]] = defaultdict(
        lambda: {"success": 0, "refusal": 0, "error": 0}
    )
    for record in records:
        model_id = resolve_chat_model_to_id(record.model_id)
        by_model[model_id][record.status.value] += 1

    summary = {
        "records_total": len(records),
        "records_success": sum(1 for item in records if item.status.value == "success"),
        "records_refusal": sum(1 for item in records if item.status.value == "refusal"),
        "records_error": sum(1 for item in records if item.status.value == "error"),
        "phase": "latest_run",
    }
    result = AnalysisResult(
        summary=summary,
        by_model=json.loads(json.dumps(by_model)),
        metrics=[
            AnalysisMetric(
                metric_name="framework_placeholder_total_records",
                value=float(summary["records_total"]),
                notes="Placeholder metric before full-scale run.",
            )
        ],
        generated_at=datetime.now(UTC),
    )
    return result.model_dump(mode="json")
