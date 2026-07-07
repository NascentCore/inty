"""Deterministic literature and analysis agent stubs."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from models import (
    AnalysisTask,
    AnalysisTaskOutput,
    LiteratureTask,
    LiteratureTaskOutput,
)

SEED_HYPOTHESIS_ID = "nucleotide_salvage"


def load_snippets(path: Path) -> list[dict]:
    """Load curated literature snippets."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    return payload


def literature_stub(task: LiteratureTask, snippets_path: Path) -> LiteratureTaskOutput:
    """Match snippets by keyword and return structured literature output."""
    snippets = load_snippets(snippets_path)
    matched = [
        snippet
        for snippet in snippets
        if any(keyword in snippet["keywords"] for keyword in task.keywords)
    ]
    assert matched
    summary = " ".join(snippet["summary"] for snippet in matched[:2])
    entity_ids = sorted(
        {
            entity_id
            for snippet in matched
            for entity_id in snippet["entities"]
        }
    )
    return LiteratureTaskOutput(
        task_id=task.task_id,
        snippet_ids=[snippet["snippet_id"] for snippet in matched[:2]],
        summary=summary,
        entity_ids=entity_ids,
        supports_hypothesis_id=task.hypothesis_id,
    )


def analysis_stub(
    task: AnalysisTask,
    dataset_path: Path,
    output_dir: Path,
) -> AnalysisTaskOutput:
    """Run deterministic metabolomics analysis for the toy dataset."""
    frame = pd.read_csv(dataset_path)
    metabolite_columns = [
        column
        for column in frame.columns
        if column not in {"sample_id", "group"}
    ]
    transformed = frame.copy()
    for column in metabolite_columns:
        transformed[column] = transformed[column].map(lambda value: math.log10(value))

    hypothermic = transformed[transformed["group"] == "hypothermic"]
    control = transformed[transformed["group"] == "control"]
    deltas = (hypothermic[metabolite_columns].mean() - control[metabolite_columns].mean()).sort_values(
        ascending=False
    )
    top_increases = deltas.head(3).index.tolist()
    top_decreases = deltas.tail(2).index.tolist()

    if task.analysis_kind == "group_diff":
        summary = (
            "Hypothermic brains show higher phosphorylated nucleotides "
            f"({', '.join(top_increases)}) and lower precursors ({', '.join(top_decreases)})."
        )
        entity_ids = top_increases + top_decreases + [SEED_HYPOTHESIS_ID]
    else:
        summary = (
            "Pathway-level pattern matches nucleotide salvage activation "
            f"with top shifts in {', '.join(top_increases)}."
        )
        entity_ids = [SEED_HYPOTHESIS_ID] + top_increases

    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / f"{task.task_id}.json"
    artifact_path.write_text(
        json.dumps(
            {
                "analysis_kind": task.analysis_kind,
                "top_increases": top_increases,
                "top_decreases": top_decreases,
                "summary": summary,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return AnalysisTaskOutput(
        task_id=task.task_id,
        output_ref=str(artifact_path),
        summary=summary,
        entity_ids=entity_ids,
        supports_hypothesis_id=task.hypothesis_id,
        top_metabolites=top_increases,
    )
