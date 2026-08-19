"""Frozen scenario and chat-recall types for Bootstrap MemDoc L1 eval."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

_CHAT_RECALL_MARKER_NAMES: frozenset[str] = frozenset(
    {"user_address", "assistant_name", "relationship_framing"}
)


class RecallProbePhase(StrEnum):
    """When a recall probe runs relative to bootstrap and dreaming."""

    POST_DOCS = "post_docs"
    PRE_DREAM = "pre_dream"
    POST_DREAM = "post_dream"


_POST_PHASES: frozenset[RecallProbePhase] = frozenset(
    {RecallProbePhase.POST_DOCS, RecallProbePhase.POST_DREAM}
)


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


class RecallProbe(BaseModel):
    """One scripted user line that probes golden-fact recall in assistant chat."""

    probe_id: str = Field(description="Unique probe key within a scenario")
    user_line: str = Field(description="User utterance sent during eval probe")
    expect_markers: tuple[str, ...] = Field(
        description="GoldenFacts field names expected in assistant reply"
    )
    phase: RecallProbePhase = Field(
        default=RecallProbePhase.POST_DREAM,
        description="Probe timing; YAML omits for POST template probes",
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
    recall_probes: tuple[RecallProbe, ...] = Field(
        description="Chat recall probes after bootstrap (POST template in YAML)"
    )

    @model_validator(mode="after")
    def _non_empty_script(self) -> BootstrapMemDocEvalScenario:
        if not self.user_turns:
            raise ValueError("user_turns must be non-empty")
        if not self.recall_probes:
            raise ValueError("recall_probes must be non-empty")
        probe_ids = [probe.probe_id for probe in self.recall_probes]
        if len(probe_ids) != len(set(probe_ids)):
            raise ValueError("probe_id values must be unique within scenario")
        for probe in self.recall_probes:
            if not probe.expect_markers:
                raise ValueError(
                    f"probe {probe.probe_id!r} must have expect_markers"
                )
            invalid = set(probe.expect_markers) - _CHAT_RECALL_MARKER_NAMES
            if invalid:
                raise ValueError(
                    f"probe {probe.probe_id!r} invalid markers: {sorted(invalid)}"
                )
        return self


class ChatTurnRecord(BaseModel):
    """One probe turn's user line and assistant downlink text."""

    probe_id: str = Field(description="Matching RecallProbe.probe_id")
    phase: RecallProbePhase = Field(description="Probe phase when turn ran")
    user_text: str = Field(description="User message sent")
    assistant_text: str = Field(description="Full assistant visible reply")


class ProbeRecallResult(BaseModel):
    """Recall result for one probe (substring or LLM judge)."""

    probe_id: str = Field(description="Matching RecallProbe.probe_id")
    phase: RecallProbePhase = Field(description="Probe phase scored")
    marker_hits: dict[str, bool] = Field(
        description="Golden marker name to hit in assistant_text"
    )
    recall_ratio: float = Field(
        description="Fraction of expect_markers hit for this probe"
    )
    judge_reasons: dict[str, str] = Field(
        description="Per-marker LLM judge rationale; empty when substring scorer"
    )


class GoldenFactsRecallScore(BaseModel):
    """Chat golden-fact recall summary for one agent eval run."""

    post_recall: float = Field(
        description="Primary metric: POST_DOCS or POST_DREAM probe hit rate"
    )
    pre_recall: float | None = Field(
        description="PRE_DREAM hit rate when pre probes ran; else null"
    )
    overall_recall: float = Field(
        description="All probe×marker hits over all probes in this run"
    )
    per_marker_recall: dict[str, float] = Field(
        description="Per golden marker hit rate across probes in this run"
    )
    per_probe: tuple[ProbeRecallResult, ...] = Field(
        description="Per-probe breakdown"
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


def golden_fact_chat_markers(golden: GoldenFacts) -> dict[str, str]:
    """Return substring needles used for chat recall scoring."""

    assert golden is not None
    return {
        "user_address": golden.user_address,
        "assistant_name": golden.assistant_name,
        "relationship_framing": golden.relationship_framing,
    }


def load_eval_scenarios(path: Path) -> tuple[BootstrapMemDocEvalScenario, ...]:
    """Load and validate scenarios YAML from repo-root-relative path."""

    assert path.is_file(), f"missing scenarios file: {path}"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    doc = BootstrapMemDocEvalScenariosFile.model_validate(raw)
    return doc.scenarios


def _probe_expect_markers(
    scenario: BootstrapMemDocEvalScenario,
    probe_id: str,
) -> tuple[str, ...]:
    for probe in scenario.recall_probes:
        if probe.probe_id == probe_id:
            return probe.expect_markers
    raise ValueError(f"unknown probe_id: {probe_id!r}")


def _phase_ratio(
    *,
    results: list[ProbeRecallResult],
    phases: frozenset[RecallProbePhase],
) -> float:
    hits = 0
    total = 0
    for result in results:
        if result.phase not in phases:
            continue
        for hit in result.marker_hits.values():
            total += 1
            if hit:
                hits += 1
    return hits / total if total else 0.0


def aggregate_probe_recall_score(
    *,
    per_probe: tuple[ProbeRecallResult, ...],
    marker_names: frozenset[str],
) -> GoldenFactsRecallScore:
    """Aggregate per-probe hits into post/pre/overall recall metrics."""

    marker_hits_total: dict[str, int] = {name: 0 for name in marker_names}
    marker_counts: dict[str, int] = {name: 0 for name in marker_names}
    for result in per_probe:
        for name, hit in result.marker_hits.items():
            if name not in marker_names:
                continue
            marker_counts[name] += 1
            if hit:
                marker_hits_total[name] += 1
    overall_hits = sum(marker_hits_total.values())
    overall_total = sum(marker_counts.values())
    per_marker_recall = {
        name: (
            marker_hits_total[name] / marker_counts[name]
            if marker_counts[name]
            else 0.0
        )
        for name in marker_names
    }
    pre_recall: float | None = None
    pre_total = sum(
        1
        for result in per_probe
        if result.phase is RecallProbePhase.PRE_DREAM
        for _ in result.marker_hits
    )
    if pre_total:
        pre_recall = _phase_ratio(
            results=list(per_probe),
            phases=frozenset({RecallProbePhase.PRE_DREAM}),
        )
    return GoldenFactsRecallScore(
        post_recall=_phase_ratio(results=list(per_probe), phases=_POST_PHASES),
        pre_recall=pre_recall,
        overall_recall=overall_hits / overall_total if overall_total else 0.0,
        per_marker_recall=per_marker_recall,
        per_probe=per_probe,
    )


def score_golden_chat_recall(
    *,
    scenario: BootstrapMemDocEvalScenario,
    chat_records: tuple[ChatTurnRecord, ...],
) -> GoldenFactsRecallScore:
    """Score golden-fact recall via substring match (unit tests / legacy)."""

    assert scenario is not None
    markers = golden_fact_chat_markers(scenario.golden_facts)
    per_probe: list[ProbeRecallResult] = []
    marker_hits_total: dict[str, int] = {name: 0 for name in markers}
    marker_counts: dict[str, int] = {name: 0 for name in markers}

    for record in chat_records:
        expect = _probe_expect_markers(scenario, record.probe_id)
        hits: dict[str, bool] = {}
        probe_hits = 0
        for name in expect:
            needle = markers[name]
            hit = needle in record.assistant_text
            hits[name] = hit
            marker_counts[name] += 1
            if hit:
                probe_hits += 1
                marker_hits_total[name] += 1
        ratio = probe_hits / len(expect) if expect else 0.0
        per_probe.append(
            ProbeRecallResult(
                probe_id=record.probe_id,
                phase=record.phase,
                marker_hits=hits,
                recall_ratio=ratio,
                judge_reasons={},
            )
        )

    return aggregate_probe_recall_score(
        per_probe=tuple(per_probe),
        marker_names=frozenset(markers),
    )


def expand_pre_dream_probes(
    probes: tuple[RecallProbe, ...],
) -> tuple[RecallProbe, ...]:
    """Copy POST template probes as PRE_DREAM for dreaming pre-agent runs."""

    assert probes is not None
    expanded: list[RecallProbe] = []
    for probe in probes:
        expanded.append(
            RecallProbe(
                probe_id=probe.probe_id,
                user_line=probe.user_line,
                expect_markers=probe.expect_markers,
                phase=RecallProbePhase.PRE_DREAM,
            )
        )
    return tuple(expanded)


def post_phase_for_awake_policy() -> RecallProbePhase:
    """POST phase label when policy is awake_write."""

    return RecallProbePhase.POST_DOCS
