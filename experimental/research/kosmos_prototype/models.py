"""Pydantic IR for the Kosmos minimal prototype."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class FindingKind(StrEnum):
    """Source channel for a finding."""

    LITERATURE = "literature"
    ANALYSIS = "analysis"


class HypothesisStatus(StrEnum):
    """Lifecycle of a scientific hypothesis."""

    OPEN = "open"
    SUPPORTED = "supported"
    REFUTED = "refuted"


class EvidenceRefType(StrEnum):
    """Pointer kind for provenance."""

    SNIPPET = "snippet"
    ANALYSIS_OUTPUT = "analysis_output"


class Entity(BaseModel):
    """Named scientific entity referenced across findings."""

    entity_id: str = Field(description="Stable entity identifier")
    kind: str = Field(description="Entity category, e.g. metabolite or pathway")
    label: str = Field(description="Human-readable label")


class Finding(BaseModel):
    """Fact produced by a literature or analysis task."""

    finding_id: str = Field(description="Stable finding identifier")
    source_task_id: str = Field(description="Task that produced this finding")
    kind: FindingKind = Field(description="Literature or analysis origin")
    summary: str = Field(description="One-sentence finding summary")
    entity_ids: list[str] = Field(description="Linked entity identifiers")
    supports_hypothesis_id: str = Field(description="Hypothesis this finding relates to")


class Hypothesis(BaseModel):
    """Testable proposition tracked across cycles."""

    hypothesis_id: str = Field(description="Stable hypothesis identifier")
    statement: str = Field(description="Hypothesis text")
    status: HypothesisStatus = Field(description="Current validation status")


class Evidence(BaseModel):
    """Provenance link from claim back to source material."""

    evidence_id: str = Field(description="Stable evidence identifier")
    ref_type: EvidenceRefType = Field(description="Snippet or analysis artifact")
    ref_id: str = Field(description="Source artifact identifier")
    finding_id: str = Field(description="Finding this evidence supports")


class Claim(BaseModel):
    """Report statement with explicit evidence backlinks."""

    claim_id: str = Field(description="Stable claim identifier")
    text: str = Field(description="Claim sentence for the report")
    evidence_ids: list[str] = Field(description="Backing evidence identifiers")


class LiteratureTask(BaseModel):
    """Literature search task specification."""

    task_id: str = Field(description="Unique task identifier")
    keywords: list[str] = Field(description="Search keywords")
    hypothesis_id: str = Field(description="Target hypothesis")


class AnalysisTask(BaseModel):
    """Data analysis task specification."""

    task_id: str = Field(description="Unique task identifier")
    analysis_kind: str = Field(description="Analysis step name")
    hypothesis_id: str = Field(description="Target hypothesis")


class TaskBatch(BaseModel):
    """Tasks proposed for one discovery cycle."""

    literature_tasks: list[LiteratureTask] = Field(description="Literature tasks")
    analysis_tasks: list[AnalysisTask] = Field(description="Analysis tasks")


class LiteratureTaskOutput(BaseModel):
    """Structured literature agent output."""

    task_id: str = Field(description="Source task identifier")
    snippet_ids: list[str] = Field(description="Matched snippet identifiers")
    summary: str = Field(description="Synthesized literature summary")
    entity_ids: list[str] = Field(description="Entities mentioned")
    supports_hypothesis_id: str = Field(description="Hypothesis supported")


class AnalysisTaskOutput(BaseModel):
    """Structured analysis agent output."""

    task_id: str = Field(description="Source task identifier")
    output_ref: str = Field(description="Artifact path or identifier")
    summary: str = Field(description="Analysis summary")
    entity_ids: list[str] = Field(description="Entities implicated")
    supports_hypothesis_id: str = Field(description="Hypothesis supported")
    top_metabolites: list[str] = Field(description="Top changed metabolites")


class CampaignInput(BaseModel):
    """Immutable campaign bootstrap input."""

    objective: str = Field(description="Research objective text")
    dataset_path: str = Field(description="Path to metabolomics CSV")
    snippets_path: str = Field(description="Path to curated paper snippets JSON")


class CycleRecord(BaseModel):
    """Persisted artifacts for one cycle."""

    cycle_index: int = Field(description="Zero-based cycle index")
    task_batch: TaskBatch = Field(description="Planned tasks")
    literature_outputs: list[LiteratureTaskOutput] = Field(description="Literature results")
    analysis_outputs: list[AnalysisTaskOutput] = Field(description="Analysis results")
    world_model_snapshot: dict = Field(description="WM JSON snapshot after ingest")
