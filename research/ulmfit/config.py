from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class VocabConfig(BaseModel):
    max_size: int = 60000
    min_freq: int = 2
    pad_token: str = "<pad>"
    unk_token: str = "<unk>"
    eos_token: str = "<eos>"


class DatasetConfig(BaseModel):
    provider: Literal["toy", "hf_imdb"] = "toy"
    lm_corpus_provider: Literal["toy", "wikitext2"] = "toy"
    toy_train_size: int = 320
    toy_valid_size: int = 64
    toy_test_size: int = 64
    imdb_train_limit: int | None = None
    imdb_valid_limit: int | None = None
    imdb_test_limit: int | None = None
    lm_train_limit: int | None = None
    lm_valid_limit: int | None = None


class ModelConfig(BaseModel):
    embedding_dim: int = 400
    hidden_dim: int = 1150
    num_layers: int = 3
    embedding_dropout: float = 0.1
    hidden_dropout: float = 0.3
    output_dropout: float = 0.4


class LmTrainConfig(BaseModel):
    bptt: int = 70
    batch_size: int = 64
    pretrain_epochs: int = 10
    finetune_epochs: int = 4
    lr_max: float = 1e-2
    weight_decay: float = 1e-5
    gradient_clip: float = 0.25
    stlr_cut_frac: float = 0.1
    stlr_ratio: float = 32.0


class ClassifierTrainConfig(BaseModel):
    batch_size: int = 64
    max_seq_len: int = 400
    fc_hidden_dim: int = 100
    num_classes: int = 2
    head_dropout: float = 0.5
    lr_max: float = 1e-2
    weight_decay: float = 1e-5
    gradient_clip: float = 0.25
    layer_lr_decay: float = 2.6
    unfreeze_blocks: list[int] = Field(default_factory=lambda: [1, 2, 4])
    stage_epochs: list[int] = Field(default_factory=lambda: [1, 1, 1])
    stlr_cut_frac: float = 0.1
    stlr_ratio: float = 32.0

    @model_validator(mode="after")
    def validate_schedule(self) -> "ClassifierTrainConfig":
        if len(self.unfreeze_blocks) != len(self.stage_epochs):
            raise ValueError("unfreeze_blocks and stage_epochs must have same length")
        return self


class ExperimentConfig(BaseModel):
    experiment_name: str
    output_dir: Path
    seed: int = 42
    device: Literal["cpu", "cuda", "auto"] = "auto"
    vocab: VocabConfig = Field(default_factory=VocabConfig)
    dataset: DatasetConfig = Field(default_factory=DatasetConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    lm_train: LmTrainConfig = Field(default_factory=LmTrainConfig)
    classifier_train: ClassifierTrainConfig = Field(
        default_factory=ClassifierTrainConfig
    )


def load_experiment_config(config_path: Path) -> ExperimentConfig:
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config = ExperimentConfig.model_validate(payload)
    if not config.output_dir.is_absolute():
        config.output_dir = (Path.cwd() / config.output_dir).resolve()
    return config
