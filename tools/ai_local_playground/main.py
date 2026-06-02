"""
CLI entry: bootstrap config then run uvicorn for the local playground.

CREATED_BY_AGENT

Usage (from repo root):

    PYTHONPATH=. python -m tools.ai_local_playground.main serve --config devops/config.yaml.local

"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Annotated

import cyclopts
from cyclopts import Parameter

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _bootstrap_config(config_yaml: str) -> str:
    path = Path(config_yaml)
    if not path.is_file():
        raise FileNotFoundError(
            f"Config not found: {path}. "
            f"Copy devops/config.yaml.local to config.yaml or pass --config."
        )
    resolved = str(path.resolve())
    os.environ["INTY_CONFIG_YAML"] = resolved
    return resolved


def _ensure_importable() -> None:
    root = str(_REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


app = cyclopts.App(
    help="Local aggregator UI for OpenRouter text + fal/Gemini image models.",
)


@app.command
def serve(
    host: Annotated[str, Parameter(help="Bind host.")] = "127.0.0.1",
    port: Annotated[int, Parameter(help="Bind port.")] = 8777,
    config: Annotated[
        str,
        Parameter(
            name="--config",
            help="Path to Inty config.yaml (sets INTY_CONFIG_YAML before imports).",
        ),
    ] = "",
) -> None:
    """Start the playground HTTP server on localhost."""
    _ensure_importable()
    config_path = config.strip() if config else ""
    if not config_path:
        for candidate in (
            _REPO_ROOT / "config.yaml",
            _REPO_ROOT / "devops" / "config.yaml.local",
        ):
            if candidate.is_file():
                config_path = str(candidate)
                break
    if not config_path:
        raise FileNotFoundError(
            "No config.yaml found. Pass --config or copy devops/config.yaml.local."
        )
    _bootstrap_config(config_path)

    import uvicorn

    from tools.ai_local_playground.server import create_app

    uvicorn.run(create_app(), host=host, port=port, log_level="info")


if __name__ == "__main__":
    app()
