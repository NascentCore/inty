"""Helpers bridging sim CLI to existing bootstrap agent creation."""

from __future__ import annotations

import io
from pathlib import Path
from typing import TextIO


def create_bootstrap_agent_id(
    *,
    repo_root: Path,
    api_base: str,
    token_path: str,
    stderr: TextIO,
) -> str:
    """Create a fresh bootstrap-test agent and return its id."""
    from tools.scripts.create_bootstrap_test_agent import run_create

    buf = io.StringIO()
    rc = run_create(
        api_base=api_base,
        token_path=token_path,
        http_timeout=60.0,
        stdout=buf,
        stderr=stderr,
    )
    if rc != 0:
        raise RuntimeError("create_bootstrap_test_agent failed")
    for line in buf.getvalue().splitlines():
        if line.startswith("[create-bootstrap-test-agent] agent_id="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("create_bootstrap_test_agent did not print agent_id")
