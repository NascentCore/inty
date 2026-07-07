"""Deterministic task planner with WM-aware and summary-only modes."""

from __future__ import annotations

from dataclasses import dataclass

from models import AnalysisTask, LiteratureTask, TaskBatch
from world_model import SEED_HYPOTHESIS_ID, WorldModelStore

SUMMARY_MAX_CHARS = 200

TASK_CATALOG: tuple[tuple[str, LiteratureTask, AnalysisTask], ...] = (
    (
        "phase_1",
        LiteratureTask(
            task_id="lit_nucleotide_salvage",
            keywords=["nucleotide", "salvage", "hypothermia"],
            hypothesis_id=SEED_HYPOTHESIS_ID,
        ),
        AnalysisTask(
            task_id="analysis_group_diff",
            analysis_kind="group_diff",
            hypothesis_id=SEED_HYPOTHESIS_ID,
        ),
    ),
    (
        "phase_2",
        LiteratureTask(
            task_id="lit_pathway_context",
            keywords=["pathway", "enrichment", "salvage"],
            hypothesis_id=SEED_HYPOTHESIS_ID,
        ),
        AnalysisTask(
            task_id="analysis_pathway_pattern",
            analysis_kind="pathway_pattern",
            hypothesis_id=SEED_HYPOTHESIS_ID,
        ),
    ),
    (
        "phase_3",
        LiteratureTask(
            task_id="lit_precursor_inversion",
            keywords=["precursor", "inversion", "salvage"],
            hypothesis_id=SEED_HYPOTHESIS_ID,
        ),
        AnalysisTask(
            task_id="analysis_confirm_salvage",
            analysis_kind="group_diff",
            hypothesis_id=SEED_HYPOTHESIS_ID,
        ),
    ),
)


@dataclass(frozen=True)
class PlannerInput:
    """Inputs required to plan the next cycle."""

    use_world_model: bool
    world_model: WorldModelStore
    last_summary: str


def plan_tasks(planner_input: PlannerInput) -> TaskBatch:
    """Select the next literature and analysis tasks for one cycle."""
    if planner_input.use_world_model:
        return _plan_with_world_model(planner_input.world_model)
    return _plan_with_summary_only(planner_input.last_summary)


def _plan_with_world_model(world_model: WorldModelStore) -> TaskBatch:
    """Use structured queries so completed tasks are not repeated."""
    open_hypotheses = world_model.query_open_hypotheses()
    if not open_hypotheses:
        return TaskBatch(literature_tasks=[], analysis_tasks=[])
    completed = set(world_model.query_completed_task_ids())
    for _phase_name, literature_task, analysis_task in TASK_CATALOG:
        pending_literature = literature_task.task_id not in completed
        pending_analysis = analysis_task.task_id not in completed
        if pending_literature or pending_analysis:
            return TaskBatch(
                literature_tasks=[literature_task] if pending_literature else [],
                analysis_tasks=[analysis_task] if pending_analysis else [],
            )
    return TaskBatch(literature_tasks=[], analysis_tasks=[])


def _plan_with_summary_only(last_summary: str) -> TaskBatch:
    """Robin-style pass-through: lossy summary cannot track completed task IDs."""
    del last_summary
    first_phase = TASK_CATALOG[0]
    return TaskBatch(
        literature_tasks=[first_phase[1]],
        analysis_tasks=[first_phase[2]],
    )
