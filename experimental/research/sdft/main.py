#!/usr/bin/env python3
"""CLI for SDFT paper reproduction (research sandbox)."""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import cyclopts
import torch
from loguru import logger

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from research.sdft.config import DatasetName, ExperimentConfig, default_upstream_dir, load_experiment_config
from research.sdft.runner import dry_run_train, run_eval, run_train, try_import_distil_trainer

app = cyclopts.App(name="sdft-repro", help="Reproduce SDFT via pinned idanshen/Self-Distillation.")

SDFT_ROOT = Path(__file__).resolve().parent
VALIDATION_LOG = SDFT_ROOT / "results" / "validation_log.md"


def _append_validation_entry(
    command: str,
    exit_code: int,
    expected: bool,
    reason: str,
    stderr_excerpt: str,
) -> str:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    block = (
        f"\n### {date}\n\n"
        f"- **command**: `{command}`\n"
        f"- **exit_code**: {exit_code}\n"
        f"- **expected**: {str(expected).lower()}\n"
        f"- **reason**: {reason}\n"
        f"- **stderr_excerpt**:\n\n```\n{stderr_excerpt.strip()}\n```\n"
    )
    return block


def _reset_validation_log() -> None:
    header = (
        "# SDFT validation log\n\n"
        "GPU/CUDA/vLLM failures on CPU-only hosts are **expected** (`expected: true`).\n"
        "Cloud GPU runs should be appended under `## Cloud GPU run`.\n"
    )
    VALIDATION_LOG.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION_LOG.write_text(header, encoding="utf-8")


def _run_shell(command: str, cwd: Path | None) -> tuple[int, str]:
    result = subprocess.run(
        command,
        shell=True,
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
    )
    stderr_tail = "\n".join(result.stderr.splitlines()[-30:])
    if stderr_tail == "" and result.stdout:
        stderr_tail = "\n".join(result.stdout.splitlines()[-30:])
    return result.returncode, stderr_tail


def _gpu_failure_reason(stderr: str) -> str | None:
    lowered = stderr.lower()
    markers = (
        "cuda",
        "gpu",
        "vllm",
        "no device",
        "out of memory",
        "cudart",
    )
    if any(marker in lowered for marker in markers):
        if "vllm" in lowered:
            return "EXPECTED_VLLM_NO_GPU"
        return "EXPECTED_GPU_MISSING"
    return None


@app.command()
def train(
    config: Annotated[
        str,
        cyclopts.Parameter(name=["--config", "-c"], help="Path to experiment yaml."),
    ],
    dry_run: Annotated[
        bool,
        cyclopts.Parameter(help="Validate dataset/config only; no trainer.train()."),
    ] = False,
) -> None:
    cfg: ExperimentConfig = load_experiment_config(Path(config).resolve())
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    if dry_run:
        dry_run_train(cfg)
        return
    run_train(cfg)


@app.command()
def eval(
    config: Annotated[
        str,
        cyclopts.Parameter(name=["--config", "-c"], help="Path to experiment yaml."),
    ],
) -> None:
    cfg: ExperimentConfig = load_experiment_config(Path(config).resolve())
    assert cfg.dataset in (DatasetName.TOOLUSE, DatasetName.SCIENCE)
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    run_eval(cfg)


@app.command()
def validate(
    config: Annotated[
        str,
        cyclopts.Parameter(
            name=["--config", "-c"],
            help="Smoke config path for train/dry-run checks.",
        ),
    ] = "research/sdft/configs/smoke.yaml",
) -> None:
    """Run CPU-oriented checks and rewrite results/validation_log.md."""
    _reset_validation_log()
    repo_root = SDFT_ROOT.parent.parent
    entries: list[str] = []
    smoke_path = Path(config)
    if smoke_path.is_file():
        smoke_config = smoke_path.resolve()
    else:
        smoke_config = (SDFT_ROOT / "configs" / "smoke.yaml").resolve()
    upstream_dir = default_upstream_dir(SDFT_ROOT)

    checks: list[tuple[str, str, Path | None]] = [
        (
            f"bash {SDFT_ROOT / 'scripts' / 'clone_upstream.sh'}",
            "clone_upstream",
            repo_root,
        ),
        (
            f"{sys.executable} -c \"import torch; print(torch.cuda.is_available())\"",
            "cuda_probe",
            repo_root,
        ),
    ]
    for command, label, cwd in checks:
        code, stderr = _run_shell(command, cwd)
        expected = False
        reason = "OK" if code == 0 else "UNEXPECTED_COMMAND_FAILED"
        if label == "cuda_probe" and code == 0:
            if "false" in stderr.strip().lower():
                reason = "EXPECTED_CUDA_NOT_AVAILABLE"
                expected = True
            else:
                reason = "OK_CUDA_AVAILABLE"
        entries.append(_append_validation_entry(command, code, expected, reason, stderr))

    ok, err = try_import_distil_trainer(upstream_dir)
    if ok:
        entries.append(_append_validation_entry("import distil_trainer", 0, False, "OK", ""))
    elif "vllm" in err.lower() or "trl.extras.vllm" in err:
        entries.append(
            _append_validation_entry(
                "import distil_trainer",
                1,
                True,
                "EXPECTED_MISSING_VLLM_EXTRA",
                err,
            )
        )
    elif _gpu_failure_reason(err) is not None:
        entries.append(
            _append_validation_entry(
                "import distil_trainer",
                1,
                True,
                _gpu_failure_reason(err) or "EXPECTED_GPU_MISSING",
                err,
            )
        )
    else:
        entries.append(
            _append_validation_entry(
                "import distil_trainer",
                1,
                False,
                "UNEXPECTED_IMPORT_FAILED",
                err,
            )
        )

    dry_cmd = (
        f"PYTHONPATH={repo_root} {sys.executable} {SDFT_ROOT / 'main.py'} "
        f"train -c {smoke_config} --dry-run"
    )
    code, stderr = _run_shell(dry_cmd, repo_root)
    if code == 0:
        entries.append(_append_validation_entry(dry_cmd, code, False, "OK", stderr))
    elif _gpu_failure_reason(stderr) is not None:
        entries.append(
            _append_validation_entry(
                dry_cmd,
                code,
                True,
                _gpu_failure_reason(stderr) or "EXPECTED_GPU_MISSING",
                stderr,
            )
        )
    else:
        entries.append(_append_validation_entry(dry_cmd, code, False, "UNEXPECTED_DRY_RUN_FAILED", stderr))

    train_cmd = (
        f"PYTHONPATH={repo_root} {sys.executable} {SDFT_ROOT / 'main.py'} train -c {smoke_config}"
    )
    code, stderr = _run_shell(train_cmd, repo_root)
    gpu_reason = _gpu_failure_reason(stderr)
    if code != 0 and gpu_reason is not None:
        entries.append(_append_validation_entry(train_cmd, code, True, gpu_reason, stderr))
    elif code != 0 and (
        "huggingface" in stderr.lower()
        or "connection" in stderr.lower()
        or "cuda" in stderr.lower()
    ):
        entries.append(
            _append_validation_entry(train_cmd, code, True, "EXPECTED_MODEL_DOWNLOAD_OR_GPU", stderr)
        )
    elif code != 0:
        entries.append(_append_validation_entry(train_cmd, code, False, "UNEXPECTED_TRAIN_FAILED", stderr))
    else:
        entries.append(_append_validation_entry(train_cmd, code, False, "OK", stderr))

    for _eval_cfg_rel, dataset in (
        ("research/sdft/configs/tooluse_7b.yaml", "tooluse"),
        ("research/sdft/configs/science_7b.yaml", "science"),
    ):
        script = "eval_tooluse.py" if dataset == "tooluse" else "eval_science.py"
        help_cmd = f"{sys.executable} {upstream_dir / script} --help"
        code, stderr = _run_shell(help_cmd, upstream_dir)
        if code != 0 and "no module named 'vllm'" in stderr.lower():
            entries.append(
                _append_validation_entry(help_cmd, code, True, "EXPECTED_VLLM_NOT_INSTALLED", stderr)
            )
        elif code != 0 and _gpu_failure_reason(stderr) is not None:
            entries.append(
                _append_validation_entry(
                    help_cmd,
                    code,
                    True,
                    _gpu_failure_reason(stderr) or "",
                    stderr,
                )
            )
        elif code != 0:
            entries.append(
                _append_validation_entry(help_cmd, code, False, "UNEXPECTED_EVAL_HELP_FAILED", stderr)
            )
        else:
            entries.append(_append_validation_entry(help_cmd, code, False, "OK", stderr))

    with VALIDATION_LOG.open("a", encoding="utf-8") as handle:
        handle.write("".join(entries))
    logger.info("Wrote validation log to {}", VALIDATION_LOG)


if __name__ == "__main__":
    app()
