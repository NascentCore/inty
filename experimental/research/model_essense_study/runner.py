from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from loguru import logger

from research.model_essense_study.config import ModelEssenseStudyConfig
from research.model_essense_study.model_client import (
    OpenRouterModelClient,
    UnsupportedModelClient,
)
from research.model_essense_study.prompting import build_messages
from research.model_essense_study.schema import (
    ExperimentManifest,
    InferenceResultRecord,
    ManifestItem,
    ResponseStatus,
)


class _ModelClient(Protocol):
    def generate(
        self,
        *,
        model_id: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        top_p: float,
        timeout_seconds: float,
    ): ...


def _run_single_record(
    *,
    cfg: ModelEssenseStudyConfig,
    model_client: _ModelClient,
    item: ManifestItem,
) -> InferenceResultRecord:
    started_at = datetime.now(UTC)
    messages = build_messages(persona=item.persona, stimulus_text=item.stimulus.text)
    metadata = {
        "temperature": item.temperature,
        "top_p": item.top_p,
        "max_tokens": item.max_tokens,
        "message_count": len(messages),
    }
    result = model_client.generate(
        model_id=item.model_id,
        messages=messages,
        temperature=item.temperature,
        max_tokens=item.max_tokens,
        top_p=item.top_p,
        timeout_seconds=cfg.inference.timeout_seconds,
    )
    finished_at = datetime.now(UTC)
    latency_ms = max(
        0.0,
        (finished_at - started_at).total_seconds() * 1000,
    )
    status_mapping = {
        "success": ResponseStatus.SUCCESS,
        "refusal": ResponseStatus.REFUSAL,
        "error": ResponseStatus.ERROR,
    }
    return InferenceResultRecord(
        run_id=item.run_id,
        task_id=item.task_id,
        model_id=item.model_id,
        persona_id=item.persona.persona_id,
        stimulus_id=item.stimulus.stimulus_id,
        repeat_index=item.repeat_index,
        status=status_mapping.get(result.status, ResponseStatus.ERROR),
        text=result.output_text or "",
        error_message=result.error_message,
        refusal_reason=result.refusal_reason,
        latency_ms=latency_ms,
        created_at=finished_at,
        metadata=metadata
        | {
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "timeout_seconds": cfg.inference.timeout_seconds,
            "model_metadata": result.metadata or {},
        },
    )


def _read_existing_task_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    task_ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = InferenceResultRecord.model_validate_json(line)
        task_ids.add(record.task_id)
    return task_ids


def run_inference(
    *,
    manifest: ExperimentManifest,
    config: ModelEssenseStudyConfig,
    max_items: int | None,
    responses_path: Path,
    real_run: bool,
    requests_per_minute: int | None,
    resume_from_existing: bool,
    openrouter_api_key: str | None,
) -> dict:
    items = list(manifest.items)
    selected = items[: max_items] if max_items is not None else items
    responses_path.parent.mkdir(parents=True, exist_ok=True)
    existing_task_ids = (
        _read_existing_task_ids(responses_path) if resume_from_existing else set()
    )
    selected_before_skip = list(selected)
    selected = [item for item in selected_before_skip if item.task_id not in existing_task_ids]
    skipped_existing_count = len(selected_before_skip) - len(selected)
    rpm = requests_per_minute or config.planning.requests_per_minute
    spacing_seconds = 60.0 / max(rpm, 1)

    if real_run:
        if not openrouter_api_key:
            raise ValueError(
                "OPENROUTER_API_KEY / OPENAI_API_KEY is required for --real-run."
            )
        model_client = OpenRouterModelClient(
            base_url=config.probe.openrouter_base_url,
            api_key=openrouter_api_key,
        )
        phase = "real_execution"
    else:
        model_client = UnsupportedModelClient()
        phase = "framework_scaffold"

    started_monotonic = time.monotonic()
    started_at_utc = datetime.now(UTC).isoformat()
    results: list[InferenceResultRecord] = []
    with responses_path.open(
        "a" if resume_from_existing else "w",
        encoding="utf-8",
    ) as output_file:
        for index, item in enumerate(selected, start=1):
            result = _run_single_record(
                cfg=config,
                model_client=model_client,
                item=item,
            )
            results.append(result)
            output_file.write(result.model_dump_json())
            output_file.write("\n")
            output_file.flush()
            if index < len(selected):
                time.sleep(spacing_seconds)

    elapsed_seconds = round(time.monotonic() - started_monotonic, 4)
    summary = {
        "run_id": manifest.run_id,
        "total_requested_items": len(items),
        "selected_items": len(selected_before_skip),
        "skipped_existing_items": skipped_existing_count,
        "executed_items": len(results),
        "status_breakdown": {
            "success": sum(1 for r in results if r.status == ResponseStatus.SUCCESS),
            "refusal": sum(1 for r in results if r.status == ResponseStatus.REFUSAL),
            "error": sum(1 for r in results if r.status == ResponseStatus.ERROR),
        },
        "phase": phase,
        "responses_path": str(responses_path),
        "real_run": real_run,
        "requests_per_minute": rpm,
        "elapsed_seconds": elapsed_seconds,
        "started_at": started_at_utc,
        "finished_at": datetime.now(UTC).isoformat(),
    }
    logger.info(
        "Inference run executed: run_id={} executed_items={} phase={}",
        summary["run_id"],
        summary["executed_items"],
        summary["phase"],
    )
    return {
        "items": [json.loads(result.model_dump_json()) for result in results],
        "summary": summary,
    }
