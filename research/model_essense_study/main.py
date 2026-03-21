#!/usr/bin/env python3
"""Model essence study CLI (framework + real execution)."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import cyclopts
from loguru import logger

from app.db.session import AsyncSessionLocal
from research.model_essense_study.analysis import run_analysis_scaffold
from research.model_essense_study.config import ModelEssenseStudyConfig, load_study_config
from research.model_essense_study.db import load_persona_raw_agents, load_stimulus_candidates
from research.model_essense_study.figures import generate_figure_placeholders
from research.model_essense_study.manifest_builder import build_manifest, save_manifest
from research.model_essense_study.model_client import (
    ModelAvailabilityResult,
    OpenRouterModelAvailabilityProbe,
)
from research.model_essense_study.persona_builder import (
    PersonaSelectionResult,
    select_personas,
)
from research.model_essense_study.report import build_scaffold_report
from research.model_essense_study.run_planner import build_run_plan
from research.model_essense_study.runner import run_inference as run_inference_job
from research.model_essense_study.schema import (
    AgentPersonaRaw,
    ExperimentManifest,
    PersonaRecord,
    StimulusRecord,
)
from research.model_essense_study.stimulus_builder import (
    StimulusBuildResult,
    build_mock_stimulus_candidates,
    build_stimuli,
)

app = cyclopts.App(
    name="model-essense-study",
    help="Roleplay model essence experiment framework.",
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_cfg(config_path: str) -> ModelEssenseStudyConfig:
    return load_study_config(Path(config_path).resolve())


def _load_manifest(path: Path) -> ExperimentManifest:
    return ExperimentManifest.model_validate_json(path.read_text(encoding="utf-8"))


def _resolve_openrouter_api_key() -> str | None:
    env_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    return env_key if env_key else None


@app.command()
def extract_personas(
    config: Annotated[
        str,
        cyclopts.Parameter(
            name=["--config", "-c"],
            help="Path to study config YAML.",
        ),
    ] = "research/model_essense_study/config.yaml",
    use_mock_data: Annotated[
        bool,
        cyclopts.Parameter(
            name="--use-mock-data",
            help="Use local mock personas instead of DB extraction.",
        ),
    ] = False,
) -> None:
    """
    Build the 10-persona scaffold dataset.
    """
    cfg = _load_cfg(config)
    raw_agents: list[AgentPersonaRaw] = []
    if use_mock_data:
        raw_agents = [
            AgentPersonaRaw(
                agent_id=f"mock-agent-{i}",
                name=f"Mock Persona {i}",
                gender="FEMALE" if i % 2 == 0 else "MALE",
                personality=(
                    "Warm and gentle, emotionally attentive."
                    if i % 4 == 0
                    else "Playful and teasing, energetic vibe."
                ),
                scenario="Daily chat companion scenario.",
                tags=["warm", "playful"] if i % 2 == 0 else ["rational", "calm"],
                meta_data={"age": 22 + i},
            )
            for i in range(1, 25)
        ]
    else:
        async def _load_from_db() -> list[AgentPersonaRaw]:
            async with AsyncSessionLocal() as db:
                return await load_persona_raw_agents(
                    db,
                    limit=max(cfg.experiment.persona_count * 20, 500),
                )

        raw_agents = asyncio.run(_load_from_db())

    result: PersonaSelectionResult = select_personas(
        candidates=raw_agents,
        target_count=cfg.experiment.persona_count,
    )

    payload = {
        "version": "personas_v1",
        "created_at": datetime.now(UTC).isoformat(),
        "target_count": cfg.experiment.persona_count,
        "selected_count": len(result.items),
        "coverage_summary": result.coverage_summary,
        "personas": [item.model_dump(mode="json") for item in result.items],
    }
    output_path = cfg.data_dir / "personas" / "personas_v1.json"
    _write_json(output_path, payload)
    logger.info("Persona scaffold written to {}", output_path)


@app.command()
def build_stimuli_dataset(
    config: Annotated[
        str,
        cyclopts.Parameter(name=["--config", "-c"], help="Path to study config YAML."),
    ] = "research/model_essense_study/config.yaml",
    use_mock_data: Annotated[
        bool,
        cyclopts.Parameter(
            name="--use-mock-data",
            help="Use local mock chat messages for framework bootstrap.",
        ),
    ] = False,
) -> None:
    """
    Build ~100 English stimuli from chat-history candidates.
    """
    cfg = _load_cfg(config)

    if use_mock_data:
        candidates = build_mock_stimulus_candidates()
    else:
        async def _load_from_db() -> list:
            async with AsyncSessionLocal() as db:
                return await load_stimulus_candidates(
                    db,
                    query_limit=cfg.stimulus.candidate_query_limit,
                )

        candidates = asyncio.run(_load_from_db())

    result: StimulusBuildResult = build_stimuli(
        candidates=candidates,
        target_count=cfg.experiment.stimulus_count,
        min_length=cfg.stimulus.min_chars,
        max_length=cfg.stimulus.max_chars,
        english_ratio_min=cfg.stimulus.english_ratio_min,
    )
    stimuli_path = cfg.data_dir / "stimuli" / "stimuli_v1.jsonl"
    summary_path = cfg.data_dir / "stimuli" / "stimuli_v1_summary.json"

    stimuli_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(item.model_dump(mode="json"), ensure_ascii=False)
        for item in result.items
    ]
    stimuli_path.write_text(
        "\n".join(lines) + ("\n" if lines else ""),
        encoding="utf-8",
    )
    _write_json(
        summary_path,
        {
            "version": "stimuli_v1",
            "created_at": datetime.now(UTC).isoformat(),
            **result.summary,
        },
    )
    logger.info("Stimuli scaffold written to {}", stimuli_path)


@app.command()
def build_manifest_file(
    config: Annotated[
        str,
        cyclopts.Parameter(name=["--config", "-c"], help="Path to study config YAML."),
    ] = "research/model_essense_study/config.yaml",
) -> None:
    """
    Build experiment manifest from personas + stimuli + model list.
    """
    cfg = _load_cfg(config)
    personas_path = cfg.data_dir / "personas" / "personas_v1.json"
    stimuli_path = cfg.data_dir / "stimuli" / "stimuli_v1.jsonl"
    manifest_path = cfg.data_dir / "manifests" / "manifest_v1.json"

    personas_payload = json.loads(personas_path.read_text(encoding="utf-8"))
    personas = [PersonaRecord.model_validate(item) for item in personas_payload["personas"]]
    stimuli = [
        StimulusRecord.model_validate_json(line)
        for line in stimuli_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not personas:
        raise ValueError(
            "No personas found. Run extract-personas first and ensure selected_count > 0."
        )
    if not stimuli:
        raise ValueError(
            "No stimuli found. Run build-stimuli-dataset first and ensure selected_count > 0."
        )

    manifest = build_manifest(
        model_ids=cfg.experiment.model_ids,
        personas=personas,
        stimuli=stimuli,
        repeats_per_cell=cfg.experiment.repeats_per_cell,
        generation=cfg.generation,
    )
    save_manifest(manifest_path, manifest)
    logger.info("Manifest written to {} (cells={})", manifest_path, manifest.total_cells)


@app.command()
def run_inference(
    config: Annotated[
        str,
        cyclopts.Parameter(name=["--config", "-c"], help="Path to study config YAML."),
    ] = "research/model_essense_study/config.yaml",
    max_records: Annotated[
        int | None,
        cyclopts.Parameter(
            name="--max-records",
            help="Cap number of manifest cells (omit for full manifest run).",
        ),
    ] = None,
    real_run: Annotated[
        bool,
        cyclopts.Parameter(
            name="--real-run",
            help="Enable real model invocation through OpenRouter endpoint.",
        ),
    ] = False,
    resume_from_existing: Annotated[
        bool,
        cyclopts.Parameter(
            name="--resume-from-existing",
            help="Append and skip task_ids already present in output file.",
        ),
    ] = False,
    requests_per_minute: Annotated[
        int | None,
        cyclopts.Parameter(
            name="--requests-per-minute",
            help="Throttle request throughput for this run.",
        ),
    ] = None,
) -> None:
    """
    Run inference and write JSONL response records.
    """
    cfg = _load_cfg(config)
    manifest = _load_manifest(cfg.manifest_path)
    responses_path = cfg.responses_real_path if real_run else cfg.responses_path
    run_summary_path = cfg.run_summary_real_path if real_run else cfg.run_summary_path

    result = run_inference_job(
        manifest=manifest,
        config=cfg,
        max_items=max_records,
        responses_path=responses_path,
        real_run=real_run,
        requests_per_minute=requests_per_minute,
        resume_from_existing=resume_from_existing,
        openrouter_api_key=_resolve_openrouter_api_key(),
    )
    _write_json(
        run_summary_path,
        result["summary"] | {"created_at": datetime.now(UTC).isoformat()},
    )
    logger.info(
        "Inference completed: real_run={} executed={}",
        real_run,
        result["summary"]["executed_items"],
    )


@app.command()
def analyze(
    config: Annotated[
        str,
        cyclopts.Parameter(name=["--config", "-c"], help="Path to study config YAML."),
    ] = "research/model_essense_study/config.yaml",
) -> None:
    """
    Run analysis from response JSONL.
    """
    cfg = _load_cfg(config)
    raw_path = cfg.responses_real_path if cfg.responses_real_path.exists() else cfg.responses_path
    analysis_path = cfg.analysis_path
    analysis_payload = run_analysis_scaffold(raw_path=raw_path)
    _write_json(analysis_path, analysis_payload)
    logger.info("Analysis scaffold completed")


@app.command()
def report(
    config: Annotated[
        str,
        cyclopts.Parameter(name=["--config", "-c"], help="Path to study config YAML."),
    ] = "research/model_essense_study/config.yaml",
) -> None:
    """
    Generate framework report and placeholder figure artifacts.
    """
    cfg = _load_cfg(config)
    analysis_path = cfg.analysis_path
    figures = generate_figure_placeholders(cfg.figures_dir)
    report_text = build_scaffold_report(
        config=cfg,
        analysis_path=analysis_path,
        figures=figures,
    )
    report_path = cfg.report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    logger.info("Report scaffold completed at {}", report_path)


@app.command()
def probe_model_availability(
    config: Annotated[
        str,
        cyclopts.Parameter(name=["--config", "-c"], help="Path to study config YAML."),
    ] = "research/model_essense_study/config.yaml",
    include_claude_todo: Annotated[
        bool,
        cyclopts.Parameter(
            name="--include-claude-todo",
            help="Include Claude TODO baseline model in probe list.",
        ),
    ] = True,
    dry_run: Annotated[
        bool,
        cyclopts.Parameter(
            name="--dry-run",
            help="Skip network probing and only record intended checks.",
        ),
    ] = False,
) -> None:
    """
    Probe configured model availability, including Claude TODO baseline.
    """
    cfg = _load_cfg(config)
    model_ids = list(cfg.experiment.model_ids)
    if include_claude_todo and cfg.probe.claude_todo_model_id not in model_ids:
        model_ids.append(cfg.probe.claude_todo_model_id)

    probe = OpenRouterModelAvailabilityProbe(
        base_url=cfg.probe.openrouter_base_url,
        api_key=_resolve_openrouter_api_key(),
    )
    results: list[ModelAvailabilityResult] = [
        probe.probe(
            model_id=model_id,
            timeout_seconds=cfg.probe.timeout_seconds,
            dry_run=dry_run,
        )
        for model_id in model_ids
    ]
    summary = {
        "total_models": len(results),
        "available_count": sum(1 for item in results if item.status == "available"),
        "skipped_count": sum(1 for item in results if item.status == "skipped"),
        "auth_error_count": sum(1 for item in results if item.status == "auth_error"),
        "unavailable_count": sum(1 for item in results if item.status == "unavailable"),
        "error_count": sum(1 for item in results if item.status == "error"),
    }
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "dry_run": dry_run,
        "base_url": cfg.probe.openrouter_base_url,
        "models": [asdict(item) for item in results],
        "summary": summary,
    }
    _write_json(cfg.model_availability_path, payload)
    logger.info(
        "Model availability probe written to {} (available={}/{})",
        cfg.model_availability_path,
        summary["available_count"],
        summary["total_models"],
    )


@app.command()
def plan_run_budget(
    config: Annotated[
        str,
        cyclopts.Parameter(name=["--config", "-c"], help="Path to study config YAML."),
    ] = "research/model_essense_study/config.yaml",
    avg_input_tokens: Annotated[
        int | None,
        cyclopts.Parameter(
            name="--avg-input-tokens",
            help="Override average input tokens per request.",
        ),
    ] = None,
    avg_output_tokens: Annotated[
        int | None,
        cyclopts.Parameter(
            name="--avg-output-tokens",
            help="Override average output tokens per request.",
        ),
    ] = None,
    requests_per_minute: Annotated[
        int | None,
        cyclopts.Parameter(
            name="--requests-per-minute",
            help="Override execution throughput estimate.",
        ),
    ] = None,
) -> None:
    """
    Compute budget and execution window estimate for full run.
    """
    cfg = _load_cfg(config)
    payload = build_run_plan(
        config=cfg,
        avg_input_tokens=avg_input_tokens,
        avg_output_tokens=avg_output_tokens,
        requests_per_minute=requests_per_minute,
    )
    _write_json(cfg.run_plan_path, payload)
    logger.info(
        "Run planning artifact written to {} (cost=${} / within_budget={})",
        cfg.run_plan_path,
        payload["cost_estimate"]["total_estimated_cost_usd"],
        payload["cost_estimate"]["within_budget_cap"],
    )


@app.default
def default_help() -> None:
    print(app.help_print())


if __name__ == "__main__":
    app()

