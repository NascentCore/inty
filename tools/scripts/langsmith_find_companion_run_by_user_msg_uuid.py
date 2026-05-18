#!/usr/bin/env python3
"""List LangSmith runs in a UTC window and find companion turns matching user_msg_uuid.

Used when debugging ``/api/v1/chat/ws`` + ``tools.inty_v2_repl`` (see
``.cursor/skills/inty-backend-inspect/SKILL.md``). Project name and API key
resolution mirror ``app/core/config.py`` LangSmith env behavior and
``tools/scripts/download_run.py``.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from langsmith import Client


def _local_username_slug() -> str:
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
    return "-".join(parts) if parts else "unknown"


def _project_from_app(app_data: dict[str, Any]) -> str:
    name = str(app_data.get("name") or "inty-backend").strip() or "inty-backend"
    env_val = str(app_data.get("environment", "dev") or "dev").strip().lower()
    proj = f"{name}-{env_val}"
    if env_val == "local":
        proj = f"{proj}-{_local_username_slug()}"
    return proj


def _langchain_api_key(yaml_data: dict[str, Any] | None) -> str | None:
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


def main() -> int:
    p = argparse.ArgumentParser(
        description=(
            "Fetch LangSmith runs from WINDOW_START_UTC (UTC) and print runs whose "
            "payload contains the given user_msg_uuid (substring scan; limit<=100)."
        )
    )
    p.add_argument(
        "--user-msg-uuid",
        required=True,
        help="REPL user-input message-uuid / companion user_msg_uuid",
    )
    p.add_argument(
        "--window-start-utc",
        required=True,
        help="ISO 8601 UTC lower bound, e.g. 2026-05-11T10:30:00+00:00",
    )
    p.add_argument(
        "--config",
        default="config.yaml",
        help="Repo-root YAML with app/agent blocks (default: config.yaml)",
    )
    p.add_argument(
        "--project-name",
        default="",
        help="Override LANGSMITH_PROJECT (default: derive from config app.*)",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=100,
        help="list_runs limit (max 100 per LangSmith API)",
    )
    args = p.parse_args()
    limit = max(1, min(int(args.limit), 100))

    cfg_path = Path(args.config)
    if not cfg_path.is_file():
        print(f"error: config not found: {cfg_path}", file=sys.stderr)
        return 1

    data = yaml.safe_load(cfg_path.read_text())
    if not isinstance(data, dict):
        print("error: config root must be a mapping", file=sys.stderr)
        return 1

    key = _langchain_api_key(data)
    if not key:
        print(
            "error: missing langchain_api_key in config.agent and env",
            file=sys.stderr,
        )
        return 1
    os.environ["LANGCHAIN_API_KEY"] = key

    app = data.get("app") if isinstance(data.get("app"), dict) else {}
    proj = (args.project_name or "").strip() or _project_from_app(app)

    uid = args.user_msg_uuid.strip()
    start = datetime.fromisoformat(args.window_start_utc.replace("Z", "+00:00"))
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)

    client = Client()
    runs = list(
        client.list_runs(project_name=proj, start_time=start, limit=limit)
    )
    print("project", proj, "runs_fetched", len(runs))

    seen: set[str] = set()
    matches: list[Any] = []
    for r in runs:
        blob = json.dumps(
            r.model_dump(mode="json"), ensure_ascii=False, default=str
        )
        hit = uid in blob or (
            r.name
            and "agentic_companion_user_turn" in r.name
            and uid in str(r.inputs or {})
        )
        if not hit:
            continue
        rid = str(r.id)
        if rid in seen:
            continue
        seen.add(rid)
        matches.append(r)

    if not matches:
        print(
            "no run containing user_msg_uuid in window "
            f"(limit={limit}); narrow/widen UTC window or check project/key"
        )
        return 0

    for r in matches:
        print("---")
        print(
            "id",
            r.id,
            "name",
            r.name,
            "status",
            r.status,
            "start_time",
            r.start_time,
        )
        inp = r.inputs or {}
        if isinstance(inp, dict):
            print("inputs.user_msg_uuid", inp.get("user_msg_uuid"))
            print("inputs.inty_trace_id", inp.get("inty_trace_id"))
        try:
            root = client.read_run(str(r.id), load_child_runs=True)
        except Exception as exc:
            print(
                "  read_run(load_child_runs=True) failed:", exc, file=sys.stderr
            )
            continue
        for ch in root.child_runs or []:
            print(
                "  child",
                ch.name,
                ch.id,
                "status",
                ch.status,
                "error",
                ch.error,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
