#!/usr/bin/env python3
from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Annotated

import cyclopts
from loguru import logger
import numpy as np
import torch

# Support direct script execution from repo root:
# python3 research/ulmfit/main.py run --config ...
if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from research.ulmfit.config import ExperimentConfig, load_experiment_config
from research.ulmfit.trainer import run_ulmfit_pipeline

app = cyclopts.App(name="ulmfit-reproduction", help="Reproduce ULMFiT with PyTorch.")


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def resolve_device(mode: str) -> torch.device:
    if mode == "cpu":
        return torch.device("cpu")
    if mode == "cuda":
        return torch.device("cuda")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


@app.command()
def run(
    config: Annotated[
        str,
        cyclopts.Parameter(
            name=["--config", "-c"],
            help="Path to experiment yaml config.",
        ),
    ] = "research/ulmfit/configs/smoke.yaml",
) -> None:
    config_path = Path(config).resolve()
    cfg: ExperimentConfig = load_experiment_config(config_path)
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    set_seed(cfg.seed)
    device = resolve_device(cfg.device)
    logger.info("Running experiment {} on {}", cfg.experiment_name, device)
    metrics = run_ulmfit_pipeline(cfg, device)
    output_path = cfg.output_dir / "metrics_summary.json"
    output_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    logger.info("Saved summary metrics to {}", output_path)


if __name__ == "__main__":
    app()
