"""Pydantic experiment config for SDFT reproduction (yaml-driven)."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class DatasetName(StrEnum):
    TOY = "toy"
    TOOLUSE = "tooluse"
    SCIENCE = "science"


class VllmMode(StrEnum):
    COLOCATE = "colocate"
    SERVER = "server"


class TrainConfig(BaseModel):
    learning_rate: float
    num_train_epochs: int
    num_prompts_per_batch: int
    ref_model_mixup_alpha: float
    max_prompt_length: int
    max_completion_length: int
    per_device_train_batch_size: int
    use_vllm: bool
    vllm_mode: VllmMode
    vllm_gpu_memory_utilization: float
    sync_ref_model: bool
    ref_model_sync_steps: int
    save_steps: int
    max_grad_norm: float
    report_to: str
    bf16: bool
    num_generations: int = Field(default=1)
    num_iterations: int = Field(default=1)
    num_loss_tokens_to_skip: int = Field(default=3)
    vllm_importance_sampling_correction: bool = Field(default=True)
    vllm_enable_sleep_mode: bool = Field(default=False)


class EvalConfig(BaseModel):
    max_new_tokens: int
    temperature: float
    model_path: str | None = None


class ExperimentConfig(BaseModel):
    experiment_name: str
    output_dir: Path
    upstream_dir: Path
    seed: int
    model_name: str
    dataset: DatasetName
    train: TrainConfig
    eval: EvalConfig


def load_experiment_config(config_path: Path) -> ExperimentConfig:
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config = ExperimentConfig.model_validate(payload)
    cwd = Path.cwd()
    if not config.output_dir.is_absolute():
        config.output_dir = (cwd / config.output_dir).resolve()
    if not config.upstream_dir.is_absolute():
        config.upstream_dir = (cwd / config.upstream_dir).resolve()
    return config


def default_upstream_dir(sdft_root: Path) -> Path:
    return (sdft_root / "upstream").resolve()
