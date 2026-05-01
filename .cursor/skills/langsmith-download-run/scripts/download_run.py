#!/usr/bin/env python3
"""Download one LangSmith run by ID to JSON (stdout or file)."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from pathlib import Path
from typing import Any

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
    agent_data = data.get("agent") if isinstance(data.get("agent"), dict) else {}
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download a LangSmith run by ID to JSON.",
    )
    parser.add_argument("run_id", help="LangSmith run UUID")
    parser.add_argument(
        "--config",
        default="config.yaml",
        metavar="PATH",
        help=(
            "Inty config.yaml: sets LANGCHAIN_API_KEY, LANGSMITH_PROJECT, "
            "LANGSMITH_TRACING_V2 (same rules as app/core/config.py). Default: config.yaml."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print resolved LANGSMITH_PROJECT and LANGSMITH_TRACING_V2 to stderr (never the API key).",
    )
    parser.add_argument(
        "--load-child-runs",
        action="store_true",
        help="Ask the API to include nested child runs on this read.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="-",
        metavar="PATH",
        help='Output path (default "-" for stdout).',
    )
    args = parser.parse_args()

    cfg = Path(args.config)
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

    if args.verbose:
        sys.stderr.write(
            "LangSmith env from config: "
            f"LANGSMITH_PROJECT={os.environ.get('LANGSMITH_PROJECT', '')!r} "
            f"LANGSMITH_TRACING_V2={os.environ.get('LANGSMITH_TRACING_V2', '')!r}\n"
        )

    from langsmith import Client

    client = Client()
    try:
        run = client.read_run(args.run_id, load_child_runs=args.load_child_runs)
    except Exception as exc:
        sys.stderr.write(f"LangSmith read_run failed for {args.run_id!r}: {exc}\n")
        return 1
    payload = run.model_dump(mode="json")
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

    if args.output == "-":
        sys.stdout.write(text)
    else:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
