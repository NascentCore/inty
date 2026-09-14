"""Helpers bridging sim CLI to existing bootstrap agent creation."""

from __future__ import annotations

import io
from pathlib import Path
from typing import TextIO

from tools.inty_v2_repl.sim_transport import DEFAULT_USER_ID, psql

_SIM_TAG = "[inty-user-sim]"


def deactivate_active_companion_bonds_for_user(
    repo_root: Path,
    config_path: Path,
    *,
    user_id: str,
) -> int:
    """Mark ACTIVE companion bonds INACTIVE for one user before --create-agent."""
    assert user_id != ""
    raw = psql(
        repo_root,
        config_path,
        f"""
UPDATE companion_bonds
SET state = 'INACTIVE',
    inactive_at = NOW()
WHERE user_id = '{user_id}'
  AND state = 'ACTIVE';
SELECT COUNT(*) FROM companion_bonds
WHERE user_id = '{user_id}' AND state = 'ACTIVE';
""",
    )
    lines = [line.strip() for line in raw.strip().splitlines() if line.strip()]
    remaining = int(lines[-1]) if lines else 0
    return remaining


def create_bootstrap_agent_id(
    *,
    repo_root: Path,
    api_base: str,
    token_path: str,
    config_path: Path,
    stderr: TextIO,
    skip_db_checks: bool,
) -> str:
    """Create a fresh bootstrap-test agent and return its id."""
    from tools.scripts.create_bootstrap_test_agent import run_create

    if not skip_db_checks:
        remaining = deactivate_active_companion_bonds_for_user(
            repo_root,
            config_path,
            user_id=DEFAULT_USER_ID,
        )
        if remaining:
            print(
                f"{_SIM_TAG} warning: {remaining} ACTIVE companion bond(s) remain "
                f"for user {DEFAULT_USER_ID!r} after deactivate",
                file=stderr,
            )
        else:
            print(
                f"{_SIM_TAG} deactivated prior ACTIVE companion bonds for "
                f"user {DEFAULT_USER_ID!r}",
                file=stderr,
            )
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
