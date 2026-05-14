#!/usr/bin/env python3
"""
Replay a chat-to-image trace request from LangSmith.

Key steps:
1) Load a trace record from LangSmith (or from a previously saved JSON file).
2) Normalize and persist the full trace runs for repeatable offline analysis.
3) Rebuild one provider request from trace inputs and replay it against real APIs.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
from datetime import date, datetime, time
from pathlib import Path
from typing import Annotated, Any, Literal

import cyclopts
from loguru import logger
from pydantic import BaseModel, Field

app = cyclopts.App(help="Fetch/save/replay LangSmith chat-to-image traces")

_DEFAULT_TRACE_DIR = Path(".inty/langsmith_traces")

_RUN_NAME_Z_IMAGE = "z_image_turbo_image_to_image"
_RUN_NAME_SEEDREAM = "seedream_v4_5_edit"
_RUN_NAME_GEMINI = "generate_image_with_google_genai"

ReplayProvider = Literal[
    "fal_z_image_turbo_image_to_image",
    "fal_seedream_v4_5_edit",
    "google_genai_generate_image",
]


class TraceRunRecord(BaseModel):
    id: str
    trace_id: str | None = None
    parent_run_id: str | None = None
    name: str | None = None
    run_type: str | None = None
    status: str | None = None
    error: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class TraceRecord(BaseModel):
    source: Literal["langsmith", "local_json"]
    project_name: str | None = None
    trace_id: str
    root_run_id: str | None = None
    fetched_at: str
    runs: list[TraceRunRecord]


class ReplayRequest(BaseModel):
    provider: ReplayProvider
    source_run_id: str
    source_run_name: str
    model: str | None = None
    prompt: str | None = None
    reference_image_urls: list[str] = Field(default_factory=list)
    gcs_uri_base: str
    provider_arguments: dict[str, Any]


class ReplayExecutionResult(BaseModel):
    provider: ReplayProvider
    source_run_id: str
    model: str | None = None
    gcs_uri: str
    gcs_http_url: str
    image_format: str
    width: int
    height: int
    generated_at: str


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, BaseModel):
        return _json_safe(value.model_dump(mode="python"))
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return _json_safe(model_dump(mode="python"))
        except TypeError:
            return _json_safe(model_dump())
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    return str(value)


def _filter_supported_kwargs(
    callable_obj: Any, kwargs: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    signature = inspect.signature(callable_obj)
    parameters = signature.parameters
    has_var_kwargs = any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )
    if has_var_kwargs:
        return (kwargs, [])

    supported_names = set(parameters.keys())
    accepted: dict[str, Any] = {}
    dropped: list[str] = []
    for key, value in kwargs.items():
        if key in supported_names:
            accepted[key] = value
        else:
            dropped.append(key)
    return (accepted, dropped)


def _normalize_run_record(run: Any) -> TraceRunRecord:
    metadata = getattr(run, "metadata", None)
    inputs = getattr(run, "inputs", None)
    outputs = getattr(run, "outputs", None)
    tags = getattr(run, "tags", None)
    return TraceRunRecord(
        id=str(getattr(run, "id", "")),
        trace_id=(
            str(getattr(run, "trace_id"))
            if getattr(run, "trace_id", None) is not None
            else None
        ),
        parent_run_id=(
            str(getattr(run, "parent_run_id"))
            if getattr(run, "parent_run_id", None) is not None
            else None
        ),
        name=_json_safe(getattr(run, "name", None)),
        run_type=_json_safe(getattr(run, "run_type", None)),
        status=_json_safe(getattr(run, "status", None)),
        error=_json_safe(getattr(run, "error", None)),
        start_time=_json_safe(getattr(run, "start_time", None)),
        end_time=_json_safe(getattr(run, "end_time", None)),
        inputs=_json_safe(inputs) if isinstance(inputs, dict) else {},
        outputs=_json_safe(outputs) if isinstance(outputs, dict) else {},
        metadata=_json_safe(metadata) if isinstance(metadata, dict) else {},
        tags=[str(t) for t in tags] if isinstance(tags, list) else [],
    )


def _choose_root_run_id(
    runs: list[TraceRunRecord], preferred_run_id: str | None
) -> str | None:
    if preferred_run_id:
        return preferred_run_id
    for run in runs:
        if run.parent_run_id is None:
            return run.id
    return runs[0].id if runs else None


def _get_project_name_explicit_or_env(project_name: str | None) -> str | None:
    if project_name:
        return project_name
    return os.getenv("LANGSMITH_PROJECT")


def _list_trace_runs(
    client: Any,
    *,
    trace_id: str,
    project_name: str | None,
    max_runs: int,
) -> list[Any]:
    kwargs: dict[str, Any] = {"trace_id": trace_id, "limit": max_runs}
    if project_name:
        kwargs["project_name"] = project_name

    filtered_kwargs, dropped = _filter_supported_kwargs(client.list_runs, kwargs)
    if dropped:
        logger.warning("list_runs() dropped unsupported kwargs: {}", dropped)
    runs = list(client.list_runs(**filtered_kwargs))
    if runs:
        return runs

    # Fallback: some SDK versions may not support trace_id filtering.
    fallback_kwargs: dict[str, Any] = {"limit": max_runs}
    if project_name:
        fallback_kwargs["project_name"] = project_name
    filtered_fallback_kwargs, dropped_fallback = _filter_supported_kwargs(
        client.list_runs, fallback_kwargs
    )
    if dropped_fallback:
        logger.warning(
            "list_runs() fallback dropped unsupported kwargs: {}",
            dropped_fallback,
        )
    candidates = list(client.list_runs(**filtered_fallback_kwargs))
    return [
        run
        for run in candidates
        if str(getattr(run, "trace_id", "")).strip() == trace_id
    ]


def _fetch_trace_record(
    *,
    run_id: str | None,
    trace_id: str | None,
    project_name: str | None,
    max_runs: int,
) -> TraceRecord:
    if not run_id and not trace_id:
        raise ValueError(
            "Pass either --run-id or --trace-id when not using --trace-record-path."
        )

    from langsmith import Client

    client = Client()
    project_name_final = _get_project_name_explicit_or_env(project_name)

    root_run_obj = None
    trace_id_final = trace_id
    if run_id:
        root_run_obj = client.read_run(run_id)
        if trace_id_final is None:
            trace_id_from_run = getattr(root_run_obj, "trace_id", None)
            if trace_id_from_run is None:
                raise ValueError(f"Run {run_id} has no trace_id in LangSmith.")
            trace_id_final = str(trace_id_from_run)

    if trace_id_final is None:
        raise ValueError("Unable to resolve trace_id.")

    run_objects = _list_trace_runs(
        client,
        trace_id=trace_id_final,
        project_name=project_name_final,
        max_runs=max_runs,
    )
    if root_run_obj is not None:
        root_id = str(getattr(root_run_obj, "id", ""))
        if root_id and all(
            str(getattr(candidate, "id", "")) != root_id for candidate in run_objects
        ):
            run_objects.append(root_run_obj)
    if not run_objects:
        raise ValueError(f"No runs found for trace_id={trace_id_final}.")

    normalized_runs = [_normalize_run_record(run) for run in run_objects]
    root_run_id = _choose_root_run_id(
        normalized_runs,
        preferred_run_id=(str(getattr(root_run_obj, "id")) if root_run_obj else None),
    )
    return TraceRecord(
        source="langsmith",
        project_name=project_name_final,
        trace_id=trace_id_final,
        root_run_id=root_run_id,
        fetched_at=datetime.utcnow().isoformat(),
        runs=normalized_runs,
    )


def _save_trace_record(trace_record: TraceRecord, save_path: Path) -> None:
    save_path.parent.mkdir(parents=True, exist_ok=True)
    save_path.write_text(
        trace_record.model_dump_json(indent=2),
        encoding="utf-8",
    )


def _load_trace_record(path: Path) -> TraceRecord:
    payload = json.loads(path.read_text(encoding="utf-8"))
    record = TraceRecord(**payload)
    return record.model_copy(update={"source": "local_json"})


def _select_source_run(
    trace_record: TraceRecord, target_run_id: str | None
) -> TraceRunRecord:
    if target_run_id:
        for run in trace_record.runs:
            if run.id == target_run_id:
                return run
        raise ValueError(f"target_run_id={target_run_id} not found in trace.")

    by_priority = [
        _RUN_NAME_Z_IMAGE,
        _RUN_NAME_SEEDREAM,
        _RUN_NAME_GEMINI,
    ]

    def _name_matches(run_name: str | None, expected: str) -> bool:
        if run_name is None:
            return False
        lowered = run_name.lower()
        return lowered == expected or expected in lowered

    for expected_name in by_priority:
        matched = [
            run for run in trace_record.runs if _name_matches(run.name, expected_name)
        ]
        if matched:
            matched.sort(key=lambda run: run.start_time or "", reverse=True)
            return matched[0]

    available = sorted({run.name or "<unnamed>" for run in trace_record.runs})
    raise ValueError(
        "No replayable run found in trace. "
        f"Expected one of: {by_priority}. Available run names: {available}"
    )


def _is_http_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def _extract_gemini_prompt(contents: list[Any]) -> str | None:
    text_parts = [
        item for item in contents if isinstance(item, str) and not _is_http_url(item)
    ]
    if not text_parts:
        return None
    if len(text_parts) == 1:
        return text_parts[0]
    return "\n".join(text_parts)


def _build_replay_request_from_run(
    run: TraceRunRecord,
    *,
    fallback_gcs_uri_base: str,
) -> ReplayRequest:
    run_name = (run.name or "").lower()
    inputs = run.inputs

    if _RUN_NAME_Z_IMAGE in run_name:
        args = inputs.get("args")
        if not isinstance(args, dict):
            raise ValueError("z-image trace inputs do not contain dict 'args'.")
        gcs_uri_base = str(inputs.get("gcs_uri_base") or fallback_gcs_uri_base)
        prompt = args.get("prompt")
        image_url = args.get("image_url")
        refs = [image_url] if _is_http_url(image_url) else []
        return ReplayRequest(
            provider="fal_z_image_turbo_image_to_image",
            source_run_id=run.id,
            source_run_name=run.name or _RUN_NAME_Z_IMAGE,
            model="fal-ai/z-image-turbo/image-to-image",
            prompt=str(prompt) if prompt is not None else None,
            reference_image_urls=refs,
            gcs_uri_base=gcs_uri_base,
            provider_arguments=args,
        )

    if _RUN_NAME_SEEDREAM in run_name:
        args = inputs.get("args")
        if not isinstance(args, dict):
            raise ValueError("seedream trace inputs do not contain dict 'args'.")
        gcs_uri_base = str(inputs.get("gcs_uri_base") or fallback_gcs_uri_base)
        prompt = args.get("prompt")
        image_urls = args.get("image_urls")
        refs = (
            [u for u in image_urls if _is_http_url(u)]
            if isinstance(image_urls, list)
            else []
        )
        return ReplayRequest(
            provider="fal_seedream_v4_5_edit",
            source_run_id=run.id,
            source_run_name=run.name or _RUN_NAME_SEEDREAM,
            model="fal-ai/bytedance/seedream/v4.5/edit",
            prompt=str(prompt) if prompt is not None else None,
            reference_image_urls=refs,
            gcs_uri_base=gcs_uri_base,
            provider_arguments=args,
        )

    if _RUN_NAME_GEMINI in run_name:
        model = inputs.get("model")
        contents = inputs.get("contents")
        if not isinstance(contents, list):
            raise ValueError("gemini trace inputs do not contain list 'contents'.")
        gcs_uri_base = str(inputs.get("gcs_uri_base") or fallback_gcs_uri_base)
        refs = [item for item in contents if _is_http_url(item)]
        return ReplayRequest(
            provider="google_genai_generate_image",
            source_run_id=run.id,
            source_run_name=run.name or _RUN_NAME_GEMINI,
            model=str(model) if model is not None else None,
            prompt=_extract_gemini_prompt(contents),
            reference_image_urls=refs,
            gcs_uri_base=gcs_uri_base,
            provider_arguments={
                "model": model,
                "contents": contents,
                "system_instructions": inputs.get("system_instructions"),
            },
        )

    raise ValueError(
        f"Unsupported run for replay: run_name={run.name!r}, run_id={run.id}"
    )


async def _execute_replay(request: ReplayRequest) -> ReplayExecutionResult:
    if request.provider == "fal_z_image_turbo_image_to_image":
        from app.core.images.fal import (
            ZImageTurboImageToImageInput,
            z_image_turbo_image_to_image,
        )

        result = await z_image_turbo_image_to_image(
            args=ZImageTurboImageToImageInput(**request.provider_arguments),
            gcs_uri_base=request.gcs_uri_base,
        )
    elif request.provider == "fal_seedream_v4_5_edit":
        from app.core.images.fal import FalSeedreamV4_5EditInput, seedream_v4_5_edit

        result = await seedream_v4_5_edit(
            args=FalSeedreamV4_5EditInput(**request.provider_arguments),
            gcs_uri_base=request.gcs_uri_base,
        )
    elif request.provider == "google_genai_generate_image":
        from app.core.google_genai.wrapped_client import get_wrapped_client

        model = request.provider_arguments.get("model")
        if not isinstance(model, str) or not model:
            raise ValueError("Gemini replay requires string model in trace inputs.")
        contents = request.provider_arguments.get("contents")
        if not isinstance(contents, list) or not contents:
            raise ValueError(
                "Gemini replay requires non-empty list contents in trace inputs."
            )
        system_instructions = request.provider_arguments.get("system_instructions")
        if system_instructions is not None and not isinstance(
            system_instructions, list
        ):
            raise ValueError("Gemini system_instructions must be list[str] or null.")
        wrapped_client = get_wrapped_client()
        result = await wrapped_client.async_generate_image(
            model=model,
            contents=[str(item) for item in contents],
            gcs_uri_base=request.gcs_uri_base,
            system_instructions=(
                [str(item) for item in system_instructions]
                if isinstance(system_instructions, list)
                else None
            ),
        )
    else:
        raise ValueError(f"Unsupported provider: {request.provider}")

    return ReplayExecutionResult(
        provider=request.provider,
        source_run_id=request.source_run_id,
        model=request.model,
        gcs_uri=result.gcs_uri,
        gcs_http_url=result.gcs_http_url,
        image_format=result.format.value,
        width=result.size.width,
        height=result.size.height,
        generated_at=result.generated_at.isoformat(),
    )


@app.default
def main(
    run_id: Annotated[
        str | None,
        cyclopts.Parameter(
            name="--run-id",
            help="LangSmith run id (recommended: root trace run id).",
            required=False,
        ),
    ] = None,
    trace_id: Annotated[
        str | None,
        cyclopts.Parameter(
            name="--trace-id",
            help="LangSmith trace id. Use when run id is unavailable.",
            required=False,
        ),
    ] = None,
    project_name: Annotated[
        str | None,
        cyclopts.Parameter(
            name="--project-name",
            help="LangSmith project name; defaults to LANGSMITH_PROJECT env.",
            required=False,
        ),
    ] = None,
    trace_record_path: Annotated[
        str | None,
        cyclopts.Parameter(
            name="--trace-record-path",
            help="Load a previously saved trace record JSON and skip LangSmith fetch.",
            required=False,
        ),
    ] = None,
    save_trace_record_path: Annotated[
        str | None,
        cyclopts.Parameter(
            name="--save-trace-record-path",
            help="Path to save normalized trace record JSON; auto path used when omitted.",
            required=False,
        ),
    ] = None,
    target_run_id: Annotated[
        str | None,
        cyclopts.Parameter(
            name="--target-run-id",
            help="Optional run id inside the trace to replay; auto-selects by provider priority when omitted.",
            required=False,
        ),
    ] = None,
    fallback_gcs_uri_base: Annotated[
        str,
        cyclopts.Parameter(
            name="--fallback-gcs-uri-base",
            help="Used only when trace does not contain gcs_uri_base.",
        ),
    ] = "chat_images/trace_replay",
    max_runs: Annotated[
        int,
        cyclopts.Parameter(
            name="--max-runs",
            help="Maximum runs fetched for one trace from LangSmith.",
        ),
    ] = 300,
    dry_run: Annotated[
        bool,
        cyclopts.Parameter(
            name="--dry-run",
            help="Do not call provider APIs; only print extracted replay request.",
        ),
    ] = False,
    output_json: Annotated[
        str | None,
        cyclopts.Parameter(
            name="--output-json",
            help="Optional output JSON path for replay request/result summary.",
            required=False,
        ),
    ] = None,
) -> None:
    """
    Examples:
      PYTHONPATH=. python tools/scripts/replay_chat_to_image_trace.py \\
        --run-id <langsmith-run-id>

      PYTHONPATH=. python tools/scripts/replay_chat_to_image_trace.py \\
        --trace-record-path .inty/langsmith_traces/<trace_id>.json \\
        --dry-run
    """
    if max_runs <= 0:
        raise ValueError("--max-runs must be > 0")
    if trace_record_path and (run_id or trace_id):
        raise ValueError("Do not combine --trace-record-path with --run-id/--trace-id.")

    if trace_record_path:
        source_path = Path(trace_record_path)
        if not source_path.exists():
            raise ValueError(f"Trace record file not found: {source_path}")
        trace_record = _load_trace_record(source_path)
        logger.debug("Loaded trace record from local file: {}", source_path)
    else:
        trace_record = _fetch_trace_record(
            run_id=run_id,
            trace_id=trace_id,
            project_name=project_name,
            max_runs=max_runs,
        )
        save_path = (
            Path(save_trace_record_path)
            if save_trace_record_path
            else (_DEFAULT_TRACE_DIR / f"{trace_record.trace_id}.json")
        )
        _save_trace_record(trace_record, save_path)
        logger.debug("Saved normalized trace record to: {}", save_path)

    source_run = _select_source_run(trace_record, target_run_id=target_run_id)
    replay_request = _build_replay_request_from_run(
        source_run,
        fallback_gcs_uri_base=fallback_gcs_uri_base,
    )

    summary: dict[str, Any] = {
        "trace": {
            "source": trace_record.source,
            "trace_id": trace_record.trace_id,
            "root_run_id": trace_record.root_run_id,
            "run_count": len(trace_record.runs),
        },
        "replay_request": _json_safe(replay_request.model_dump(mode="python")),
    }
    if dry_run:
        summary["mode"] = "dry_run"
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        if output_json:
            output_path = Path(output_json)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Saved output summary to: {output_path}")
        return

    replay_result = asyncio.run(_execute_replay(replay_request))
    summary["mode"] = "live_replay"
    summary["replay_result"] = _json_safe(replay_result.model_dump(mode="python"))

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if output_json:
        output_path = Path(output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Saved output summary to: {output_path}")


if __name__ == "__main__":
    app()
