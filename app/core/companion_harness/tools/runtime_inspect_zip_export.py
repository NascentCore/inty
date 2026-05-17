"""Write companion_runtime_inspect debug bundles under INTY_OPS_WORKSPACE."""

from __future__ import annotations

import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langsmith import Client

from app.core.companion_harness.runtime_mode import inty_runtime_mode_is_debug

_EXPORT_LANGSMITH_MAX_RUNS = 200


def ops_debug_workspace_dir() -> Path:
    raw = os.environ.get("INTY_OPS_WORKSPACE", "").strip()
    if raw:
        return Path(raw)
    log_file = os.environ.get("INTY_LOG_FILE", "").strip()
    if log_file:
        return Path(log_file).parent
    return Path.cwd() / ".inty"


def _langchain_api_key() -> str | None:
    for env_name in ("LANGCHAIN_API_KEY", "LANGSMITH_API_KEY"):
        v = (os.environ.get(env_name) or "").strip()
        if v:
            return v
    return None


def _fetch_langsmith_trace_document(
    *,
    langsmith_trace_id: str,
) -> tuple[dict[str, Any] | None, str | None]:
    api_key = _langchain_api_key()
    if not api_key:
        return None, "LANGCHAIN_API_KEY or LANGSMITH_API_KEY not set"
    project_name = (os.environ.get("LANGSMITH_PROJECT") or "").strip() or None
    client = Client(api_key=api_key)
    runs: list[Any] = []
    kwargs: dict[str, Any] = {"trace_id": langsmith_trace_id, "limit": _EXPORT_LANGSMITH_MAX_RUNS}
    if project_name:
        kwargs["project_name"] = project_name
    try:
        runs = list(client.list_runs(**kwargs))
    except TypeError:
        kwargs.pop("trace_id", None)
        try:
            candidates = list(client.list_runs(limit=min(_EXPORT_LANGSMITH_MAX_RUNS, 100)))
            runs = [
                r
                for r in candidates
                if str(getattr(r, "trace_id", "")).strip() == langsmith_trace_id
            ]
        except Exception as exc:
            return None, str(exc)
    except Exception as exc:
        return None, str(exc)
    if not runs:
        return None, f"No runs found for trace_id={langsmith_trace_id!r}"
    return (
        {
            "download_kind": "langsmith_trace",
            "trace_id": langsmith_trace_id,
            "project_name": project_name,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "run_count": len(runs),
            "runs": [r.model_dump(mode="json") for r in runs],
        },
        None,
    )


def _zip_stem_from_correlation(correlation: dict[str, Any] | None) -> str:
    if isinstance(correlation, dict):
        u = str(correlation.get("user_msg_uuid") or "").strip()
        if u:
            return u
        t = str(correlation.get("trace_id") or "").strip()
        if t:
            return t
    return "unknown"


def write_runtime_inspect_zip(
    *,
    payload: dict[str, Any],
    correlation: dict[str, Any] | None,
) -> Path:
    assert inty_runtime_mode_is_debug()
    workspace = ops_debug_workspace_dir()
    out_dir = workspace / "runtime_inspect"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = _zip_stem_from_correlation(correlation)
    zip_path = out_dir / f"{stem}_{ts}.zip"
    members: list[str] = []
    langsmith_error: str | None = None
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        snapshot_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        zf.writestr("inspect_snapshot.json", snapshot_bytes)
        members.append("inspect_snapshot.json")

        log_file = os.environ.get("INTY_LOG_FILE", "").strip()
        if log_file:
            log_path = Path(log_file)
            if log_path.is_file():
                zf.write(log_path, arcname="inty.log")
                members.append("inty.log")

        ls_tid = ""
        if isinstance(correlation, dict):
            ls_tid = str(correlation.get("langsmith_trace_id") or "").strip()
        if ls_tid:
            trace_doc, err = _fetch_langsmith_trace_document(langsmith_trace_id=ls_tid)
            if trace_doc is not None:
                zf.writestr(
                    "langsmith_trace.json",
                    json.dumps(trace_doc, ensure_ascii=False, indent=2).encode("utf-8"),
                )
                members.append("langsmith_trace.json")
            else:
                langsmith_error = err

        export_abs = str(zip_path.resolve())
        try:
            export_rel = str(zip_path.resolve().relative_to(Path.cwd().resolve()))
        except ValueError:
            export_rel = export_abs

        manifest: dict[str, Any] = {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "correlation": correlation,
            "zip_members": members,
            "export_zip_absolute_path": export_abs,
            "export_zip_repo_relative_path": export_rel,
        }
        if langsmith_error:
            manifest["langsmith_error"] = langsmith_error
        zf.writestr(
            "manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
        )
    return zip_path


def zip_export_paths(zip_path: Path) -> tuple[str, str]:
    export_abs = str(zip_path.resolve())
    try:
        export_rel = str(zip_path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        export_rel = export_abs
    return export_abs, export_rel
