"""Append-only structured world model for cross-agent coordination."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from models import (
    AnalysisTaskOutput,
    Claim,
    Entity,
    Evidence,
    EvidenceRefType,
    Finding,
    FindingKind,
    Hypothesis,
    HypothesisStatus,
    LiteratureTaskOutput,
)


SEED_HYPOTHESIS_ID = "nucleotide_salvage"
SEED_ENTITIES = (
    Entity(entity_id="nucleotide_salvage", kind="pathway", label="Nucleotide salvage"),
    Entity(entity_id="IMP", kind="metabolite", label="Inosine monophosphate"),
    Entity(entity_id="UMP", kind="metabolite", label="Uridine monophosphate"),
    Entity(entity_id="CMP", kind="metabolite", label="Cytidine monophosphate"),
    Entity(entity_id="adenine", kind="metabolite", label="Adenine"),
    Entity(entity_id="cytidine", kind="metabolite", label="Cytidine"),
)


@dataclass
class WorldModelStore:
    """Minimal Kosmos-style structured world model."""

    entities: dict[str, Entity] = field(default_factory=dict)
    hypotheses: dict[str, Hypothesis] = field(default_factory=dict)
    findings: dict[str, Finding] = field(default_factory=dict)
    evidence: dict[str, Evidence] = field(default_factory=dict)
    claims: dict[str, Claim] = field(default_factory=dict)
    completed_task_ids: set[str] = field(default_factory=set)
    _finding_counter: int = 0
    _evidence_counter: int = 0
    _claim_counter: int = 0

    @classmethod
    def seed(cls) -> WorldModelStore:
        """Bootstrap campaign with objective-aligned hypothesis."""
        store = cls()
        for entity in SEED_ENTITIES:
            store.entities[entity.entity_id] = entity
        store.hypotheses[SEED_HYPOTHESIS_ID] = Hypothesis(
            hypothesis_id=SEED_HYPOTHESIS_ID,
            statement=(
                "Hypothermic neuroprotection engages nucleotide salvage, "
                "raising phosphorylated nucleotides while precursors fall."
            ),
            status=HypothesisStatus.OPEN,
        )
        return store

    def query_open_hypotheses(self) -> list[Hypothesis]:
        """Return hypotheses still under investigation."""
        return [
            hypothesis
            for hypothesis in self.hypotheses.values()
            if hypothesis.status == HypothesisStatus.OPEN
        ]

    def query_completed_task_ids(self) -> list[str]:
        """Return finished task identifiers for planner deduplication."""
        return sorted(self.completed_task_ids)

    def ingest_literature_output(self, output: LiteratureTaskOutput) -> None:
        """Materialize literature findings and evidence into the world model."""
        self.completed_task_ids.add(output.task_id)
        self._finding_counter += 1
        finding_id = f"F{self._finding_counter}"
        self.findings[finding_id] = Finding(
            finding_id=finding_id,
            source_task_id=output.task_id,
            kind=FindingKind.LITERATURE,
            summary=output.summary,
            entity_ids=output.entity_ids,
            supports_hypothesis_id=output.supports_hypothesis_id,
        )
        for snippet_id in output.snippet_ids:
            self._evidence_counter += 1
            evidence_id = f"E{self._evidence_counter}"
            self.evidence[evidence_id] = Evidence(
                evidence_id=evidence_id,
                ref_type=EvidenceRefType.SNIPPET,
                ref_id=snippet_id,
                finding_id=finding_id,
            )
        self._refresh_hypothesis_status(output.supports_hypothesis_id)

    def ingest_analysis_output(self, output: AnalysisTaskOutput) -> None:
        """Materialize analysis findings and evidence into the world model."""
        self.completed_task_ids.add(output.task_id)
        self._finding_counter += 1
        finding_id = f"F{self._finding_counter}"
        self.findings[finding_id] = Finding(
            finding_id=finding_id,
            source_task_id=output.task_id,
            kind=FindingKind.ANALYSIS,
            summary=output.summary,
            entity_ids=output.entity_ids,
            supports_hypothesis_id=output.supports_hypothesis_id,
        )
        self._evidence_counter += 1
        evidence_id = f"E{self._evidence_counter}"
        self.evidence[evidence_id] = Evidence(
            evidence_id=evidence_id,
            ref_type=EvidenceRefType.ANALYSIS_OUTPUT,
            ref_id=output.output_ref,
            finding_id=finding_id,
        )
        self._refresh_hypothesis_status(output.supports_hypothesis_id)

    def build_claims(self) -> list[Claim]:
        """Create report claims from supported hypotheses."""
        claims: list[Claim] = []
        for hypothesis in self.hypotheses.values():
            if hypothesis.status != HypothesisStatus.SUPPORTED:
                continue
            related_evidence = [
                evidence.evidence_id
                for evidence in self.evidence.values()
                if evidence.finding_id in {
                    finding.finding_id
                    for finding in self.findings.values()
                    if finding.supports_hypothesis_id == hypothesis.hypothesis_id
                }
            ]
            self._claim_counter += 1
            claim_id = f"C{self._claim_counter}"
            claims.append(
                Claim(
                    claim_id=claim_id,
                    text=hypothesis.statement,
                    evidence_ids=related_evidence,
                )
            )
            self.claims[claim_id] = claims[-1]
        return claims

    def render_summary(self, max_chars: int) -> str:
        """Produce a lossy text summary for Robin-style ablation."""
        lines: list[str] = []
        for hypothesis in self.hypotheses.values():
            lines.append(f"Hypothesis {hypothesis.hypothesis_id} is {hypothesis.status}.")
        for finding in list(self.findings.values())[-2:]:
            lines.append(f"Recent finding: {finding.summary}")
        text = " ".join(lines)
        return text[:max_chars]

    def snapshot(self) -> dict:
        """Serialize full world model for inspection and persistence."""
        return {
            "entities": [entity.model_dump() for entity in self.entities.values()],
            "hypotheses": [hypothesis.model_dump() for hypothesis in self.hypotheses.values()],
            "findings": [finding.model_dump() for finding in self.findings.values()],
            "evidence": [item.model_dump() for item in self.evidence.values()],
            "claims": [claim.model_dump() for claim in self.claims.values()],
            "completed_task_ids": sorted(self.completed_task_ids),
        }

    def save_snapshot(self, path: Path) -> None:
        """Persist snapshot JSON to disk."""
        path.write_text(json.dumps(self.snapshot(), indent=2), encoding="utf-8")

    def _refresh_hypothesis_status(self, hypothesis_id: str) -> None:
        """Promote hypothesis when literature and analysis both support it."""
        hypothesis = self.hypotheses[hypothesis_id]
        kinds = {
            finding.kind
            for finding in self.findings.values()
            if finding.supports_hypothesis_id == hypothesis_id
        }
        if FindingKind.LITERATURE in kinds and FindingKind.ANALYSIS in kinds:
            self.hypotheses[hypothesis_id] = Hypothesis(
                hypothesis_id=hypothesis.hypothesis_id,
                statement=hypothesis.statement,
                status=HypothesisStatus.SUPPORTED,
            )
