#!/usr/bin/env python3
"""Download one LangSmith run or an entire trace (all runs sharing trace_id) to JSON.

When ``-o``/``--output`` is omitted, writes under repo-root ``.inty/langsmith_runs/`` or
``.inty/langsmith_traces/`` (cwd-relative; run from repo root). Use ``-o -`` for stdout.

CLI is defined with Cyclopts; run ``--help`` for defaults and path rules.
"""

from __future__ import annotations

import getpass
import inspect
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Iterator

import cyclopts
import yaml

# Mirrors app/core/config.py:set_langsmith_environment_variables (project naming + tracing flag).


def _langsmith_local_username_slug() -> str:
    user = (os.getenv("USER") or os.getenv("USERNAME") or "").strip()
    if not user:
        try:
            user = getpass.getuser()
        except Exception:
            user = ""
    if not user:
        user = "unknown"
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in user)
    parts = [p for p in safe.split("-") if p]
    slug = "-".join(parts)
    return slug or "unknown"


def _langsmith_project_from_app_yaml(app_data: dict[str, Any]) -> str:
    name = str(app_data.get("name") or "inty-backend").strip() or "inty-backend"
    raw_env = app_data.get("environment", "dev")
    env_val = str(raw_env).strip().lower() if raw_env is not None else "dev"
    project = f"{name}-{env_val}"
    if env_val == "local":
        project = f"{project}-{_langsmith_local_username_slug()}"
    return project


def _tracing_v2_from_agent_yaml(agent_data: dict[str, Any]) -> bool:
    raw = agent_data.get("langsmith_tracing_enabled", True)
    if raw is None:
        return True
    return bool(raw)


def _apply_langsmith_from_config_yaml(data: dict[str, Any]) -> None:
    app_data = data.get("app") if isinstance(data.get("app"), dict) else {}
    agent_data = (
        data.get("agent") if isinstance(data.get("agent"), dict) else {}
    )
    os.environ["LANGSMITH_PROJECT"] = _langsmith_project_from_app_yaml(app_data)
    os.environ["LANGSMITH_TRACING_V2"] = (
        "true" if _tracing_v2_from_agent_yaml(agent_data) else "false"
    )


def _langchain_api_key(*, yaml_data: dict[str, Any] | None) -> str | None:
    if isinstance(yaml_data, dict):
        agent = yaml_data.get("agent")
        if isinstance(agent, dict):
            raw = agent.get("langchain_api_key")
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
    for env_name in ("LANGCHAIN_API_KEY", "LANGSMITH_API_KEY"):
        v = (os.environ.get(env_name) or "").strip()
        if v:
            return v
    return None


def _project_name_explicit_or_env(project_override: str | None) -> str | None:
    if project_override:
        return project_override
    return os.getenv("LANGSMITH_PROJECT")


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


def _iter_trace_runs(
    client: Any,
    *,
    trace_id: str,
    project_name: str | None,
    max_runs: int | None,
) -> Iterator[Any]:
    """Yield runs for ``trace_id``; LangSmith SDK paginates when ``limit`` is omitted."""
    kwargs: dict[str, Any] = {"trace_id": trace_id}
    if project_name:
        kwargs["project_name"] = project_name
    if max_runs is not None:
        kwargs["limit"] = max_runs

    filtered_kwargs, dropped = _filter_supported_kwargs(
        client.list_runs, kwargs
    )
    if dropped:
        sys.stderr.write(
            f"list_runs() dropped unsupported kwargs (ignored): {dropped}\n"
        )
    yield from client.list_runs(**filtered_kwargs)


def _fallback_runs_for_trace(
    client: Any,
    *,
    trace_id: str,
    project_name: str | None,
    max_runs: int | None,
) -> list[Any]:
    """When ``list_runs(trace_id=...)`` is unsupported or returns nothing, scan project."""
    cap = max_runs if max_runs is not None else 10_000
    kwargs: dict[str, Any] = {"limit": min(cap, 100)}
    if project_name:
        kwargs["project_name"] = project_name

    filtered_fallback_kwargs, dropped_fallback = _filter_supported_kwargs(
        client.list_runs, kwargs
    )
    if dropped_fallback:
        sys.stderr.write(
            "list_runs() fallback dropped unsupported kwargs (ignored): "
            f"{dropped_fallback}\n"
        )
    candidates = list(client.list_runs(**filtered_fallback_kwargs))
    return [
        run
        for run in candidates
        if str(getattr(run, "trace_id", "")).strip() == trace_id
    ]


def _fetch_all_runs_for_trace(
    client: Any,
    *,
    trace_id: str,
    project_name: str | None,
    max_runs: int | None,
    seed_run_obj: Any | None,
) -> tuple[list[Any], str]:
    run_objects = list(
        _iter_trace_runs(
            client,
            trace_id=trace_id,
            project_name=project_name,
            max_runs=max_runs,
        )
    )
    if not run_objects:
        run_objects = _fallback_runs_for_trace(
            client,
            trace_id=trace_id,
            project_name=project_name,
            max_runs=max_runs,
        )
    if seed_run_obj is not None:
        seed_run_id = str(getattr(seed_run_obj, "id", ""))
        if seed_run_id and all(
            str(getattr(candidate, "id", "")) != seed_run_id
            for candidate in run_objects
        ):
            run_objects.append(seed_run_obj)
    if not run_objects:
        raise ValueError(f"No runs found for trace_id={trace_id}.")
    return run_objects, trace_id


def _main_impl(
    *,
    run_id: str | None,
    config: Path,
    verbose: bool,
    load_child_runs: bool,
    trace_id: str | None,
    entire_trace: bool,
    project_name: str | None,
    max_runs: int | None,
    output: str | None,
) -> int:
    trace_id_arg = (trace_id or "").strip()
    if entire_trace and trace_id_arg:
        sys.stderr.write("Use either --trace-id or --entire-trace, not both.\n")
        return 2
    if entire_trace and not run_id:
        sys.stderr.write("--entire-trace requires --run-id.\n")
        return 2
    if trace_id_arg and run_id:
        sys.stderr.write("Do not pass --run-id together with --trace-id.\n")
        return 2
    if not trace_id_arg and not entire_trace and not run_id:
        sys.stderr.write(
            "Pass --run-id, or --trace-id UUID, or --entire-trace with --run-id.\n"
        )
        return 2
    if max_runs is not None and max_runs < 1:
        sys.stderr.write("--max-runs must be >= 1 when set.\n")
        return 2

    cfg = Path(config)
    yaml_data: dict[str, Any] | None = None
    if cfg.is_file():
        try:
            loaded = yaml.safe_load(cfg.read_text(encoding="utf-8"))
        except OSError as exc:
            sys.stderr.write(f"Cannot read config {cfg.resolve()}: {exc}\n")
            return 2
        except yaml.YAMLError as exc:
            sys.stderr.write(f"Invalid YAML in {cfg.resolve()}: {exc}\n")
            return 2
        yaml_data = loaded if isinstance(loaded, dict) else None

    if yaml_data is not None:
        _apply_langsmith_from_config_yaml(yaml_data)

    api_key = _langchain_api_key(yaml_data=yaml_data)
    if not api_key:
        sys.stderr.write(
            "Missing LangSmith credential: set agent.langchain_api_key in "
            f"{cfg.resolve()} (when using --config) or export LANGCHAIN_API_KEY / LANGSMITH_API_KEY.\n"
        )
        return 2
    os.environ["LANGCHAIN_API_KEY"] = api_key

    if verbose:
        sys.stderr.write(
            "LangSmith env from config: "
            f"LANGSMITH_PROJECT={os.environ.get('LANGSMITH_PROJECT', '')!r} "
            f"LANGSMITH_TRACING_V2={os.environ.get('LANGSMITH_TRACING_V2', '')!r}\n"
        )

    from langsmith import Client

    client = Client()
    project_for_trace = _project_name_explicit_or_env(project_name)

    trace_resolved_for_default_path: str | None = None

    if trace_id_arg or entire_trace:
        if load_child_runs:
            sys.stderr.write(
                "--load-child-runs applies only to single-run mode (omit for trace).\n"
            )
            return 2
        seed_run_obj = None
        trace_id_final = trace_id_arg
        if entire_trace:
            try:
                seed_run_obj = client.read_run(run_id)
            except Exception as exc:
                sys.stderr.write(
                    f"LangSmith read_run failed for seed {run_id!r}: {exc}\n"
                )
                return 1
            tid = getattr(seed_run_obj, "trace_id", None)
            if tid is None:
                sys.stderr.write(
                    f"Run {run_id!r} has no trace_id in LangSmith.\n"
                )
                return 1
            trace_id_final = str(tid)

        try:
            run_objects, trace_id_out = _fetch_all_runs_for_trace(
                client,
                trace_id=trace_id_final,
                project_name=project_for_trace,
                max_runs=max_runs,
                seed_run_obj=seed_run_obj,
            )
        except ValueError as exc:
            sys.stderr.write(f"{exc}\n")
            return 1
        except Exception as exc:
            sys.stderr.write(
                f"LangSmith trace fetch failed for trace_id={trace_id_final!r}: {exc}\n"
            )
            return 1

        runs_payload = [r.model_dump(mode="json") for r in run_objects]
        trace_resolved_for_default_path = trace_id_out
        payload: dict[str, Any] = {
            "download_kind": "langsmith_trace",
            "trace_id": trace_id_out,
            "project_name": project_for_trace,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "run_count": len(runs_payload),
            "runs": runs_payload,
        }
    else:
        try:
            run = client.read_run(run_id, load_child_runs=load_child_runs)
        except Exception as exc:
            sys.stderr.write(
                f"LangSmith read_run failed for {run_id!r}: {exc}\n"
            )
            return 1
        payload = run.model_dump(mode="json")

    if output is not None:
        out_target = output
    elif trace_id_arg:
        out_target = str(
            Path(".inty/langsmith_traces") / f"{trace_id_arg}.json"
        )
    elif entire_trace:
        assert trace_resolved_for_default_path is not None
        out_target = str(
            Path(".inty/langsmith_traces")
            / f"{trace_resolved_for_default_path}.json"
        )
    else:
        out_target = str(Path(".inty/langsmith_runs") / f"{run_id}.json")

    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

    if out_target == "-":
        sys.stdout.write(text)
    else:
        out = Path(out_target)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    return 0


app = cyclopts.App(
    help=(
        "Download one LangSmith run, or every run in a trace (same trace_id), to JSON.\n\n"
        "If -o/--output is omitted, writes under ./.inty/ (relative to cwd; run from repo root):\n"
        "  single run:     .inty/langsmith_runs/<run_id>.json\n"
        "  --trace-id:     .inty/langsmith_traces/<trace_id>.json\n"
        "  --entire-trace: .inty/langsmith_traces/<resolved_trace_id>.json\n"
        "Use -o - for stdout.\n\n"
        "Trace mode uses LangSmith cursor pagination; omit --max-runs to fetch all spans "
        "in the trace."
    ),
)


@app.default
def main(
    run_id: Annotated[
        str | None,
        cyclopts.Parameter(
            name="run_id",
            help=(
                "LangSmith run UUID: single-run download, or seed run for --entire-trace. "
                "May be passed positionally. Not used with --trace-id."
            ),
        ),
    ] = None,
    *,
    config: Annotated[
        Path,
        cyclopts.Parameter(
            "--config",
            help=(
                "Inty YAML for LANGCHAIN_API_KEY, LANGSMITH_PROJECT, LANGSMITH_TRACING_V2 "
                "(default: devops/config.yaml.local for local Ops companion traces)."
            ),
        ),
    ] = Path("devops/config.yaml.local"),
    verbose: Annotated[
        bool,
        cyclopts.Parameter(
            "--verbose",
            help="Print LANGSMITH_PROJECT and LANGSMITH_TRACING_V2 to stderr (not the API key).",
        ),
    ] = False,
    load_child_runs: Annotated[
        bool,
        cyclopts.Parameter(
            "--load-child-runs",
            help="Single-run only: include nested child runs from read_run.",
        ),
    ] = False,
    trace_id: Annotated[
        str | None,
        cyclopts.Parameter(
            "--trace-id",
            help="Download all runs with this trace_id (flat list; parent_run_id encodes tree).",
        ),
    ] = None,
    entire_trace: Annotated[
        bool,
        cyclopts.Parameter(
            "--entire-trace",
            help="Resolve trace_id from --run-id, then download every run in that trace.",
        ),
    ] = False,
    project_name: Annotated[
        str | None,
        cyclopts.Parameter(
            "--project-name",
            help="LangSmith project for list_runs; default LANGSMITH_PROJECT from config.",
        ),
    ] = None,
    max_runs: Annotated[
        int | None,
        cyclopts.Parameter(
            "--max-runs",
            help="Optional cap on total runs fetched for a trace; omit for no cap.",
        ),
    ] = None,
    output: Annotated[
        str | None,
        cyclopts.Parameter(
            name=("-o", "--output"),
            help='Output path; omit for .inty/ default. Use "-" for stdout.',
        ),
    ] = None,
) -> None:
    raise SystemExit(
        _main_impl(
            run_id=run_id,
            config=config,
            verbose=verbose,
            load_child_runs=load_child_runs,
            trace_id=trace_id,
            entire_trace=entire_trace,
            project_name=project_name,
            max_runs=max_runs,
            output=output,
        )
    )


if __name__ == "__main__":
    app()
