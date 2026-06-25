#!/usr/bin/env python3
"""Companion-harness scoped dead-code cleanup: ruff F401 fix + vulture report.

Generated entirely by Cursor agent.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import cyclopts
from loguru import logger

app = cyclopts.App(
    help=(
        "Clean companion-harness scope only: ruff unused-import fix and "
        "vulture high-confidence dead-code report."
    )
)

VULTURE_MIN_CONFIDENCE = 80
RUFF_SELECT_UNUSED_IMPORT = "F401"

# Companion-harness allowlist per root AGENTS.md; do not scan legacy app/ trees.
COMPANION_SCOPE_REL_PATHS: tuple[str, ...] = (
    "app/core/companion_harness",
    "app/living_sphere",
    "app/techno_core",
    "app/schemas/chat_websocket.py",
    "app/services/agentic_companion",
    "app/services/agentic_channel",
    "app/services/companion_chat_service.py",
    "app/api/v1/endpoints/chat_ws.py",
    "app/api/v1/endpoints/chat_ws_boundary.py",
    "app/api/v1/endpoints/chat_ws_companion_support.py",
    "backend/ops/weixin_channel",
    "backend/ops/telegram_channel",
    "backend/ops/api/v1/agent_channel.py",
    "backend/ops/api/v1/telegram.py",
    "tests/app/core/companion_harness",
    "tests/living_sphere",
)


@dataclass(frozen=True)
class ScopePaths:
    repo_root: Path
    paths: tuple[Path, ...]


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


def _resolve_scope(repo_root: Path) -> ScopePaths:
    resolved: list[Path] = []
    for rel in COMPANION_SCOPE_REL_PATHS:
        path = (repo_root / rel).resolve()
        if not path.exists():
            msg = f"companion scope path missing: {rel}"
            logger.error(msg)
            raise FileNotFoundError(msg)
        resolved.append(path)
    return ScopePaths(repo_root=repo_root, paths=tuple(resolved))


def _run_command(command: tuple[str, ...]) -> CommandResult:
    logger.info("run {}", " ".join(command))
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    return CommandResult(
        command=command,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _print_command_result(result: CommandResult) -> None:
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", file=sys.stderr)


def _path_args(scope: ScopePaths) -> tuple[str, ...]:
    return tuple(str(path) for path in scope.paths)


def run_ruff_fix_imports(scope: ScopePaths) -> CommandResult:
    command = (
        sys.executable,
        "-m",
        "ruff",
        "check",
        "--select",
        RUFF_SELECT_UNUSED_IMPORT,
        "--fix",
        *_path_args(scope),
    )
    return _run_command(command)


def run_vulture_report(
    scope: ScopePaths,
    whitelist: Path | None,
) -> CommandResult:
    command: list[str] = [
        sys.executable,
        "-m",
        "vulture",
        *_path_args(scope),
        "--min-confidence",
        str(VULTURE_MIN_CONFIDENCE),
    ]
    if whitelist is not None:
        command.extend(["--whitelist", str(whitelist)])
    return _run_command(tuple(command))


@app.default
def main(
    repo_root: Annotated[
        str,
        cyclopts.Parameter(
            name="--repo-root",
            help="Repository root (default: cwd).",
        ),
    ] = ".",
    fix_imports: Annotated[
        bool,
        cyclopts.Parameter(
            name="--fix-imports",
            help="Run ruff --select F401 --fix on companion scope.",
        ),
    ] = True,
    report_dead: Annotated[
        bool,
        cyclopts.Parameter(
            name="--report-dead",
            help=(
                "Run vulture with --min-confidence 80 on companion scope "
                "(report only)."
            ),
        ),
    ] = True,
    vulture_whitelist: Annotated[
        str | None,
        cyclopts.Parameter(
            name="--vulture-whitelist",
            help=(
                "Optional vulture whitelist file for dynamic references "
                "(e.g. pytest fixtures, __getattr__ exports)."
            ),
        ),
    ] = None,
) -> None:
    """Run companion-harness cleanup tools; exits 1 when vulture finds hits."""
    if not fix_imports and not report_dead:
        print("Nothing to do: enable --fix-imports and/or --report-dead.")
        raise SystemExit(2)

    root = Path(repo_root).resolve()
    scope = _resolve_scope(root)
    whitelist_path = (
        Path(vulture_whitelist).resolve() if vulture_whitelist else None
    )
    if whitelist_path is not None and not whitelist_path.is_file():
        print(f"[ERROR] vulture whitelist not found: {whitelist_path}")
        raise SystemExit(2)

    exit_code = 0

    if fix_imports:
        ruff_result = run_ruff_fix_imports(scope)
        _print_command_result(ruff_result)
        if ruff_result.returncode not in (0, 1):
            print(
                "[ERROR] ruff failed "
                f"(exit {ruff_result.returncode}); is ruff installed?"
            )
            raise SystemExit(ruff_result.returncode)

    if report_dead:
        vulture_result = run_vulture_report(scope, whitelist_path)
        _print_command_result(vulture_result)
        if vulture_result.returncode not in (0, 3):
            print(
                "[ERROR] vulture failed "
                f"(exit {vulture_result.returncode}); is vulture installed?"
            )
            raise SystemExit(vulture_result.returncode)
        if vulture_result.returncode == 3:
            exit_code = 1

    if exit_code == 0:
        print("Companion-harness dead-code cleanup finished with no vulture hits.")
    else:
        print(
            "Vulture reported high-confidence dead code; review before deleting."
        )
    raise SystemExit(exit_code)


if __name__ == "__main__":
    app()
