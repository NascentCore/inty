"""Delegate training and eval to pinned upstream Self-Distillation."""

from __future__ import annotations

import os
import subprocess
import sys
from contextlib import chdir
from pathlib import Path

from loguru import logger

from research.sdft.config import DatasetName, ExperimentConfig
from research.sdft.data_toy import build_toy_dataset


def _assert_upstream_ready(upstream_dir: Path) -> None:
    assert upstream_dir.is_dir(), f"upstream missing: {upstream_dir}; run scripts/clone_upstream.sh"
    assert (upstream_dir / "distil_trainer.py").is_file()
    assert (upstream_dir / "main.py").is_file()


def _upstream_on_path(upstream_dir: Path) -> None:
    upstream_str = str(upstream_dir.resolve())
    if upstream_str not in sys.path:
        sys.path.insert(0, upstream_str)


def load_train_dataset(cfg: ExperimentConfig):
    assert cfg.dataset is not None
    if cfg.dataset == DatasetName.TOY:
        return build_toy_dataset(cfg.seed)
    _assert_upstream_ready(cfg.upstream_dir)
    _upstream_on_path(cfg.upstream_dir)
    with chdir(cfg.upstream_dir):
        import main as upstream_main  # noqa: WPS433

        if cfg.dataset == DatasetName.TOOLUSE:
            dataset, _ = upstream_main.load_tooluse_dataset(cfg.seed)
            return dataset
        if cfg.dataset == DatasetName.SCIENCE:
            dataset, _ = upstream_main.load_science_dataset(cfg.seed)
            return dataset
    raise AssertionError(f"unsupported dataset: {cfg.dataset}")


def _eval_script_for_dataset(dataset: DatasetName) -> str:
    match dataset:
        case DatasetName.TOOLUSE:
            return "eval_tooluse.py"
        case DatasetName.SCIENCE:
            return "eval_science.py"
        case DatasetName.TOY:
            raise AssertionError("toy dataset has no upstream eval script")


def build_distil_config(cfg: ExperimentConfig):
    _assert_upstream_ready(cfg.upstream_dir)
    _upstream_on_path(cfg.upstream_dir)
    from distil_config import DistilConfig  # noqa: WPS433

    t = cfg.train
    return DistilConfig(
        seed=cfg.seed,
        use_vllm=t.use_vllm,
        vllm_mode=t.vllm_mode.value,
        vllm_tensor_parallel_size=1,
        vllm_gpu_memory_utilization=t.vllm_gpu_memory_utilization,
        vllm_enable_sleep_mode=t.vllm_enable_sleep_mode,
        learning_rate=t.learning_rate,
        warmup_ratio=0.1,
        lr_scheduler_type="cosine",
        logging_steps=1,
        bf16=t.bf16,
        fp16=False,
        per_device_train_batch_size=t.per_device_train_batch_size,
        gradient_accumulation_steps=t.num_prompts_per_batch,
        max_prompt_length=t.max_prompt_length,
        max_completion_length=t.max_completion_length,
        num_train_epochs=t.num_train_epochs,
        num_iterations=t.num_iterations,
        num_generations=t.num_generations,
        save_steps=t.save_steps,
        max_grad_norm=t.max_grad_norm,
        report_to=t.report_to,
        output_dir=str(cfg.output_dir),
        log_completions=False,
        sync_ref_model=t.sync_ref_model,
        ref_model_sync_steps=t.ref_model_sync_steps,
        ref_model_mixup_alpha=t.ref_model_mixup_alpha,
        vllm_importance_sampling_correction=t.vllm_importance_sampling_correction,
        num_loss_tokens_to_skip=t.num_loss_tokens_to_skip,
        alpha=0.0,
    )


def dry_run_train(cfg: ExperimentConfig) -> None:
    """Validate wiring without loading full weights or calling trainer.train()."""
    _assert_upstream_ready(cfg.upstream_dir)
    dataset = load_train_dataset(cfg)
    assert len(dataset) >= 1
    distil_config = build_distil_config(cfg)
    assert distil_config.output_dir == str(cfg.output_dir)
    logger.info(
        "dry_run ok: dataset={} rows={} output_dir={}",
        cfg.dataset,
        len(dataset),
        cfg.output_dir,
    )


def run_train(cfg: ExperimentConfig) -> None:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    _assert_upstream_ready(cfg.upstream_dir)
    _upstream_on_path(cfg.upstream_dir)
    from distil_trainer import DistilTrainer  # noqa: WPS433

    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    dataset = load_train_dataset(cfg)
    dtype = torch.bfloat16 if cfg.train.bf16 else torch.float32
    model = AutoModelForCausalLM.from_pretrained(cfg.model_name, torch_dtype=dtype)
    teacher_model = AutoModelForCausalLM.from_pretrained(cfg.model_name, torch_dtype=dtype)
    tokenizer = AutoTokenizer.from_pretrained(cfg.model_name)
    distil_config = build_distil_config(cfg)
    trainer = DistilTrainer(
        model=model,
        ref_model=teacher_model,
        args=distil_config,
        train_dataset=dataset,
        processing_class=tokenizer,
    )
    trainer.train()


def run_eval(cfg: ExperimentConfig) -> None:
    _assert_upstream_ready(cfg.upstream_dir)
    script_name = _eval_script_for_dataset(cfg.dataset)
    script_path = cfg.upstream_dir / script_name
    assert script_path.is_file(), f"missing {script_path}"
    model_path = cfg.eval.model_path
    assert model_path is not None and model_path != ""
    model_path = str(Path(model_path).resolve())
    output_dir = str(cfg.output_dir.resolve())
    cmd = [
        sys.executable,
        script_name,
        "--model_path",
        model_path,
        "--output_dir",
        output_dir,
        "--max_new_tokens",
        str(cfg.eval.max_new_tokens),
        "--temperature",
        str(cfg.eval.temperature),
    ]
    env = os.environ.copy()
    upstream_str = str(cfg.upstream_dir.resolve())
    env["PYTHONPATH"] = upstream_str + os.pathsep + env.get("PYTHONPATH", "")
    logger.info("eval subprocess: cwd={} cmd={}", cfg.upstream_dir, " ".join(cmd))
    subprocess.run(cmd, cwd=cfg.upstream_dir, env=env, check=True)


def try_import_distil_trainer(upstream_dir: Path) -> tuple[bool, str]:
    try:
        _assert_upstream_ready(upstream_dir)
        _upstream_on_path(upstream_dir)
        import distil_trainer  # noqa: F401, WPS433

        return True, ""
    except Exception as exc:  # noqa: BLE001 — validation harness
        return False, f"{type(exc).__name__}: {exc}"
