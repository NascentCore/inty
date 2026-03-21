from __future__ import annotations

from datetime import UTC, datetime

from loguru import logger

from research.model_essense_study.config import ModelEssenseStudyConfig
from research.model_essense_study.model_client import UnsupportedModelClient
from research.model_essense_study.prompting import build_messages
from research.model_essense_study.schema import (
    InferenceResultRecord,
    ManifestItem,
    ResponseStatus,
)


def _run_single_record(
    *,
    cfg: ModelEssenseStudyConfig,
    model_client: UnsupportedModelClient,
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


def run_inference_scaffold(
    *,
    manifest: dict,
    config: ModelEssenseStudyConfig,
    max_items: int,
) -> dict:
    items = [ManifestItem.model_validate(obj) for obj in manifest.get("items", [])]
    selected = items[: max(0, max_items)]
    model_client = UnsupportedModelClient()
    results = [
        _run_single_record(
            cfg=config,
            model_client=model_client,
            item=item,
        )
        for item in selected
    ]
    summary = {
        "run_id": manifest.get("run_id"),
        "total_requested_items": len(items),
        "executed_items": len(results),
        "status_breakdown": {
            "success": sum(1 for r in results if r.status == ResponseStatus.SUCCESS),
            "refusal": sum(1 for r in results if r.status == ResponseStatus.REFUSAL),
            "error": sum(1 for r in results if r.status == ResponseStatus.ERROR),
        },
        "phase": "framework_scaffold",
    }
    logger.info(
        "Inference scaffold executed: run_id={} executed_items={}",
        summary["run_id"],
        summary["executed_items"],
    )
    return {
        "items": [result.model_dump(mode="json") for result in results],
        "summary": summary,
    }
