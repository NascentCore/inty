from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = ""
    db: str = "inty"


class StimulusConfig(BaseModel):
    target_count: int = 100
    candidate_query_limit: int = 20000
    min_chars: int = 8
    max_chars: int = 400
    english_ratio_min: float = 0.75


class ExperimentConfig(BaseModel):
    persona_count: int = 10
    stimulus_count: int = 100
    repeats_per_cell: int = 3
    model_ids: list[str] = Field(
        default_factory=lambda: [
            "google/gemini-2.5-pro",
            "google/gemini-2.5-flash",
            "google/gemini-2.5-flash-lite",
        ]
    )


class GenerationConfig(BaseModel):
    temperature: float = 0.7
    top_p: float = 1.0
    max_tokens: int = 512


class InferenceConfig(BaseModel):
    timeout_seconds: float = 30.0
    dry_run: bool = True
    requests_per_minute: int | None = None


class PlanningConfig(BaseModel):
    repeat_semantics: str = (
        "cell-level repeats: each (model, persona, stimulus) cell is repeated N times"
    )
    avg_input_tokens: int = 220
    avg_output_tokens: int = 280
    requests_per_minute: int = 20
    fallback_input_price_per_1m_usd: float = 1.0
    fallback_output_price_per_1m_usd: float = 3.0
    budget_cap_usd: float = 100.0
    execution_window_hours: float = 12.0


class ProbeConfig(BaseModel):
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    claude_todo_model_id: str = "anthropic/claude-3.5-sonnet"
    timeout_seconds: float = 20.0


class PathsConfig(BaseModel):
    data_dir: str = "research/model_essense_study/data"
    results_dir: str = "research/model_essense_study/results"
    docs_dir: str = "research/model_essense_study/docs"


class ModelEssenseStudyConfig(BaseModel):
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    stimulus: StimulusConfig = Field(default_factory=StimulusConfig)
    experiment: ExperimentConfig = Field(default_factory=ExperimentConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    inference: InferenceConfig = Field(default_factory=InferenceConfig)
    planning: PlanningConfig = Field(default_factory=PlanningConfig)
    probe: ProbeConfig = Field(default_factory=ProbeConfig)
    load_time_utc_iso: str = Field(default="")

    @property
    def data_dir(self) -> Path:
        return Path(self.paths.data_dir).resolve()

    @property
    def results_dir(self) -> Path:
        return Path(self.paths.results_dir).resolve()

    @property
    def docs_dir(self) -> Path:
        return Path(self.paths.docs_dir).resolve()

    @property
    def personas_path(self) -> Path:
        return self.data_dir / "personas" / "personas_v1.json"

    @property
    def stimuli_path(self) -> Path:
        return self.data_dir / "stimuli" / "stimuli_v1.jsonl"

    @property
    def stimuli_summary_path(self) -> Path:
        return self.data_dir / "stimuli" / "stimuli_v1_summary.json"

    @property
    def manifest_path(self) -> Path:
        return self.data_dir / "manifests" / "manifest_v1.json"

    @property
    def responses_path(self) -> Path:
        return self.results_dir / "latest" / "raw" / "responses_scaffold.jsonl"

    @property
    def responses_real_path(self) -> Path:
        return self.results_dir / "latest" / "raw" / "responses_real.jsonl"

    @property
    def run_summary_path(self) -> Path:
        return self.results_dir / "latest" / "run_summary.json"

    @property
    def run_summary_real_path(self) -> Path:
        return self.results_dir / "latest" / "run_summary_real.json"

    @property
    def analysis_path(self) -> Path:
        return self.results_dir / "latest" / "analysis" / "analysis_summary.json"

    @property
    def metrics_snapshot_path(self) -> Path:
        return self.results_dir / "latest" / "analysis" / "metrics_snapshot.json"

    @property
    def figures_dir(self) -> Path:
        return self.results_dir / "latest" / "figures"

    @property
    def report_path(self) -> Path:
        return self.results_dir / "latest" / "report.md"

    @property
    def model_availability_path(self) -> Path:
        return self.docs_dir / "MODEL_AVAILABILITY_LATEST.json"

    @property
    def run_plan_path(self) -> Path:
        return self.docs_dir / "RUN_PLAN_LATEST.json"


def load_study_config(path: Path) -> ModelEssenseStudyConfig:
    if not path.exists():
        raise FileNotFoundError(f"study config not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cfg = ModelEssenseStudyConfig.model_validate(payload)
    cfg.load_time_utc_iso = datetime.now(UTC).isoformat()
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    cfg.results_dir.mkdir(parents=True, exist_ok=True)
    cfg.docs_dir.mkdir(parents=True, exist_ok=True)
    return cfg
