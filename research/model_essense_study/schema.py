"""Schema definitions for model essence study framework."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ResponseStatus(StrEnum):
    SUCCESS = "success"
    REFUSAL = "refusal"
    ERROR = "error"


class AgentPersonaRaw(BaseModel):
    agent_id: str
    name: str
    gender: str | None = None
    personality: str | None = None
    scenario: str | None = None
    tags: list[str] = Field(default_factory=list)
    meta_data: dict[str, Any] = Field(default_factory=dict)


class PersonaRecord(BaseModel):
    persona_id: str
    source_agent_id: str
    source_agent_name: str
    gender: str
    age_band: str
    personality_cluster: str
    personality_text: str
    scenario_text: str
    tags: list[str] = Field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Gender: {self.gender}",
            f"Age Band: {self.age_band}",
            f"Personality Cluster: {self.personality_cluster}",
        ]
        if self.personality_text:
            lines.append(f"Personality: {self.personality_text}")
        if self.scenario_text:
            lines.append(f"Scenario: {self.scenario_text}")
        if self.tags:
            lines.append("Tags: " + ", ".join(self.tags))
        return "\n".join(lines)


class StimulusCandidateRecord(BaseModel):
    candidate_id: str
    text: str
    source_chat_message_id: int
    source_session_id_hash: str
    created_at: str | None = None


class StimulusRecord(BaseModel):
    stimulus_id: str
    text: str
    source_chat_id_hash: str
    source_message_id: int
    language: str = "en"
    char_count: int
    english_ratio: float
    topic_bucket: str


class GenerationConfig(BaseModel):
    temperature: float
    top_p: float
    max_tokens: int


class ManifestItem(BaseModel):
    run_id: str
    task_id: str
    model_id: str
    persona: PersonaRecord
    stimulus: StimulusRecord
    persona_id: str
    stimulus_id: str
    repeat_index: int
    temperature: float
    top_p: float
    max_tokens: int


class ExperimentManifest(BaseModel):
    run_id: str
    created_at: datetime
    model_ids: list[str]
    personas_count: int
    stimuli_count: int
    repeats_per_cell: int
    generation: GenerationConfig
    items: list[ManifestItem]
    total_cells: int


class InferenceResultRecord(BaseModel):
    run_id: str
    task_id: str
    model_id: str
    persona_id: str
    stimulus_id: str
    repeat_index: int
    status: ResponseStatus
    text: str
    error_message: str | None = None
    refusal_reason: str | None = None
    latency_ms: float | None = None
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalysisMetric(BaseModel):
    metric_name: str
    value: float
    notes: str | None = None


class AnalysisResult(BaseModel):
    summary: dict[str, Any]
    by_model: dict[str, dict[str, int]] = Field(default_factory=dict)
    metrics: list[AnalysisMetric] = Field(default_factory=list)
    generated_at: datetime

