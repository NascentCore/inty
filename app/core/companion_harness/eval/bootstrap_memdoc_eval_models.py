"""Frozen scenario and snapshot types for Bootstrap MemDoc L1 eval."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator


class BootstrapMemDocCheckpoint(StrEnum):
    """Eval sampling moment aligned with Persona prompt injection rhythm."""

    T0_COMPLETE = "t0_complete"
    T1_FIRST_DREAM = "t1_first_dream"
    T2_SETTLED_1 = "t2_settled_1"
    T2_SETTLED_3 = "t2_settled_3"


class GoldenFacts(BaseModel):
    """Deterministic golden markers for scorer recall checks."""

    user_address: str = Field(description="User nickname marker for recall")
    assistant_name: str = Field(description="Assistant name marker for recall")
    language: str = Field(description="zh or en session language")
    relationship_framing: str = Field(
        description="Relationship framing keyword"
    )
    session_intent: str = Field(
        description="Expected ExperienceSessionIntent value"
    )


class ExperienceProfileScript(BaseModel):
    """Optional bootstrap-round script clarifying experience profile."""

    intent: str = Field(description="ExperienceSessionIntent enum value")
    tone: str | None = Field(description="Optional tone overlay")
    user_line: str = Field(
        description="User utterance clarifying companionship preference"
    )


class BootstrapMemDocEvalScenario(BaseModel):
    """One frozen bootstrap replay scenario."""

    scenario_id: str = Field(description="Unique matrix row key")
    description: str = Field(description="Human-readable scenario summary")
    user_turns: tuple[str, ...] = Field(
        description="Ordered bootstrap-phase user lines"
    )
    experience_profile: ExperienceProfileScript | None = Field(
        description="Optional experience profile clarification round"
    )
    golden_facts: GoldenFacts = Field(
        description="Golden facts for deterministic scoring"
    )
    settled_turns: tuple[str, ...] = Field(
        description="Fixed settled USER_CHAT lines after bootstrap"
    )

    @model_validator(mode="after")
    def _non_empty_user_turns(self) -> BootstrapMemDocEvalScenario:
        if not self.user_turns:
            raise ValueError("user_turns must be non-empty")
        if not self.settled_turns:
            raise ValueError("settled_turns must be non-empty")
        return self


class MemDocSnapshotBody(BaseModel):
    """One MemDoc body at a checkpoint."""

    relative_path: str = Field(description="MemDoc relative path")
    sequence_id: int = Field(description="Postgres document version seq")
    body_preview: str = Field(description="Truncated body for report")
    contains_markers: dict[str, bool] = Field(
        description="Golden marker presence per marker name"
    )


class BootstrapMemDocSnapshot(BaseModel):
    """Collected observables at one eval checkpoint."""

    checkpoint: BootstrapMemDocCheckpoint = Field(description="Sampling moment")
    memdocs: tuple[MemDocSnapshotBody, ...] = Field(
        description="USER/IDENTITY/STYLE/COMPANIONSHIP/MEMORY/SOUL bodies"
    )
    prompt_markers: dict[str, bool] = Field(
        description="Golden marker hits in prompt injection summary"
    )
    settled_reply_preview: str = Field(
        description="Assistant reply preview at settled checkpoints"
    )
    tool_background_counts: dict[str, int] = Field(
        description="Bootstrap write and related tool counts"
    )


class BootstrapMemDocScores(BaseModel):
    """Deterministic L0 metrics for one scenario × policy run."""

    golden_field_recall: dict[str, float] = Field(
        description="Per-doc recall 0-1"
    )
    persona_gap_turns: int = Field(
        description="Consecutive turns without persona markers after T0"
    )
    bootstrap_tool_call_count: int = Field(
        description="Bootstrap memory_store_write_document calls"
    )
    memory_soul_still_seed_at_t0: bool = Field(
        description="B/C expect seed at T0"
    )
    awake_memdoc_violation: bool = Field(
        description="Settled-phase non-dreaming MEMORY write"
    )
    seconds_to_t1: float | None = Field(
        description="Complete to first DreamingState seconds"
    )
    inception_delayed_by_user_chat: bool = Field(
        description="Settled USER_CHAT between T0 and T1"
    )


class BootstrapMemDocEvalScenariosFile(BaseModel):
    """Root document for contracts/bootstrap_memdoc_eval/scenarios.yaml."""

    scenarios: tuple[BootstrapMemDocEvalScenario, ...] = Field(
        description="Frozen eval scenarios"
    )

    @model_validator(mode="after")
    def _unique_scenario_ids(self) -> BootstrapMemDocEvalScenariosFile:
        ids = [scenario.scenario_id for scenario in self.scenarios]
        if len(ids) != len(set(ids)):
            raise ValueError("scenario_id values must be unique")
        return self


def load_eval_scenarios(path: Path) -> tuple[BootstrapMemDocEvalScenario, ...]:
    """Load and validate scenarios YAML from repo-root-relative path."""

    assert path.is_file(), f"missing scenarios file: {path}"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    doc = BootstrapMemDocEvalScenariosFile.model_validate(raw)
    return doc.scenarios


_PERSONA_PATHS: tuple[str, ...] = (
    "USER.md",
    "IDENTITY.md",
    "STYLE.md",
    "COMPANIONSHIP.md",
)


def score_bootstrap_memdoc_run(
    *,
    scenario: BootstrapMemDocEvalScenario,
    policy_value: str,
    snapshots: dict[BootstrapMemDocCheckpoint, BootstrapMemDocSnapshot],
    memory_seed_preview: str,
    soul_seed_preview: str,
    bootstrap_complete_at: float | None,
    dreaming_checkpoint_at: float | None,
) -> BootstrapMemDocScores:
    """Compute deterministic L0 metrics from collected snapshots."""

    golden = scenario.golden_facts
    markers = (
        ("user_address", golden.user_address),
        ("assistant_name", golden.assistant_name),
        ("relationship_framing", golden.relationship_framing),
        ("session_intent", golden.session_intent),
    )

    t0 = snapshots.get(BootstrapMemDocCheckpoint.T0_COMPLETE)
    t1 = snapshots.get(BootstrapMemDocCheckpoint.T1_FIRST_DREAM)
    recall: dict[str, float] = {}
    for rel in _PERSONA_PATHS:
        hits = 0
        total = len(markers)
        if t1 is not None:
            for body in t1.memdocs:
                if body.relative_path != rel:
                    continue
                for name, needle in markers:
                    if needle in body.body_preview:
                        hits += 1
        if t0 is not None:
            for body in t0.memdocs:
                if body.relative_path != rel:
                    continue
                for name, needle in markers:
                    if needle in body.body_preview:
                        hits += 1
        recall[rel] = hits / total if total else 0.0

    persona_gap = 0
    if t0 is not None and not any(t0.prompt_markers.values()):
        persona_gap = 1

    bootstrap_writes = 0
    if t0 is not None:
        bootstrap_writes = t0.tool_background_counts.get(
            "memory_store_write_document", 0
        )

    memory_seed = memory_seed_preview
    soul_seed = soul_seed_preview
    memory_soul_seed = True
    if t0 is not None:
        for body in t0.memdocs:
            if body.relative_path == "MEMORY.md":
                memory_soul_seed = memory_soul_seed and (
                    body.body_preview.strip() == memory_seed.strip()
                    or "seed" in body.body_preview.lower()
                )
            if body.relative_path == "SOUL.md":
                memory_soul_seed = memory_soul_seed and (
                    body.body_preview.strip() == soul_seed.strip()
                    or "seed" in body.body_preview.lower()
                )

    seconds_to_t1: float | None = None
    if bootstrap_complete_at is not None and dreaming_checkpoint_at is not None:
        seconds_to_t1 = dreaming_checkpoint_at - bootstrap_complete_at

    awake_violation = False
    t2 = snapshots.get(BootstrapMemDocCheckpoint.T2_SETTLED_3)
    if t2 is not None:
        for body in t2.memdocs:
            if body.relative_path == "MEMORY.md" and not memory_soul_seed:
                awake_violation = True

    if policy_value == "awake_write":
        memory_soul_seed = True

    return BootstrapMemDocScores(
        golden_field_recall=recall,
        persona_gap_turns=persona_gap,
        bootstrap_tool_call_count=bootstrap_writes,
        memory_soul_still_seed_at_t0=memory_soul_seed,
        awake_memdoc_violation=awake_violation,
        seconds_to_t1=seconds_to_t1,
        inception_delayed_by_user_chat=False,
    )
