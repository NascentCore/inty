"""
Smoke test for scope inner-tick worker (#3255 / PR #3387).

Verifies:
1. Optional: running Ops/inty logs show scope worker startup.
2. In-process: Postgres scope listing + one ``run_scope_inner_tick_poll_cycle`` without WS.

Run from repo root with venv + INTY_CONFIG_YAML (or devops/config.yaml.local):

  INTY_CONFIG_YAML=devops/config.yaml.local \\
  python3 .cursor/skills/scripts/inty_backend_smoke_tests/test_scope_inner_tick_worker.py \\
    --api-base http://127.0.0.1:8001

Ops should be running for log + health checks; cycle still runs if DB is reachable.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

_VERIFY_TAG = "[inty-server-module-verify]"


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in (here, *here.parents):
        if (p / "pyproject.toml").is_file() and (p / "app").is_dir():
            return p
    raise RuntimeError("Cannot find Inty repo root")


def _emit_verify_result(
    *,
    ok: bool,
    exit_code: int,
    detail: str = "",
    elapsed_s: float | None = None,
) -> None:
    if ok:
        timing = f", elapsed={elapsed_s:.2f}s" if elapsed_s is not None else ""
        print(f"{_VERIFY_TAG} RESULT: PASS (exit={exit_code}{timing})", flush=True)
    else:
        suffix = f" — {detail}" if detail else ""
        print(
            f"{_VERIFY_TAG} RESULT: FAIL (exit={exit_code}){suffix}",
            file=sys.stderr,
            flush=True,
        )


def _health_ok(api_base: str) -> bool:
    url = f"{api_base.rstrip('/')}/health"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _log_has_worker_started(repo_root: Path, workspace: Path | None) -> bool:
    log_dir = workspace if workspace is not None else repo_root / ".inty"
    log_path = log_dir / "inty.log"
    if not log_path.is_file():
        return False
    tail = log_path.read_text(encoding="utf-8", errors="replace")[-120_000:]
    return (
        "scope-inner-tick-worker: started" in tail
        or "scope_inner_tick_worker started poll_seconds=" in tail
    )


async def _run_scope_poll_cycle() -> tuple[int, str]:
    from app.core.companion_harness.memory.companion_scope_listing import (
        list_companion_memory_scopes,
    )
    from app.db.session import AsyncSessionLocal
    from app.services.agentic_companion.scope_inner_tick_poll import (
        run_scope_inner_tick_poll_cycle,
    )

    async with AsyncSessionLocal() as db:
        scopes = await list_companion_memory_scopes(db)
    scope_count = len(scopes)
    stop = asyncio.Event()
    await run_scope_inner_tick_poll_cycle(stop=stop)
    return scope_count, "cycle_ok"


def main() -> int:
    t0 = time.perf_counter()
    parser = argparse.ArgumentParser(description="Scope inner-tick worker smoke (#3255)")
    parser.add_argument(
        "--api-base",
        default=os.environ.get("INTY_API_BASE_URL", "http://127.0.0.1:8001"),
    )
    parser.add_argument(
        "--workspace",
        default=os.environ.get("INTY_WORKSPACE", ""),
        help="Log directory (default .inty under repo root)",
    )
    parser.add_argument(
        "--skip-server-check",
        action="store_true",
        help="Only run in-process scope poll cycle",
    )
    args = parser.parse_args()

    repo_root = _find_repo_root()
    os.chdir(repo_root)
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    if not os.environ.get("INTY_CONFIG_YAML"):
        local_cfg = repo_root / "devops" / "config.yaml.local"
        if local_cfg.is_file():
            os.environ["INTY_CONFIG_YAML"] = str(local_cfg)

    workspace = Path(args.workspace).resolve() if args.workspace else None

    if not args.skip_server_check:
        if not _health_ok(args.api_base):
            _emit_verify_result(
                ok=False,
                exit_code=1,
                detail=f"health check failed for {args.api_base}",
                elapsed_s=time.perf_counter() - t0,
            )
            return 1
        if not _log_has_worker_started(repo_root, workspace):
            _emit_verify_result(
                ok=False,
                exit_code=2,
                detail="scope worker startup not found in inty.log (start Ops first)",
                elapsed_s=time.perf_counter() - t0,
            )
            return 2
        print(f"{_VERIFY_TAG} server health OK; scope worker startup seen in log")

    try:
        scope_count, status = asyncio.run(_run_scope_poll_cycle())
    except Exception as exc:
        _emit_verify_result(
            ok=False,
            exit_code=3,
            detail=f"scope poll cycle raised: {exc}",
            elapsed_s=time.perf_counter() - t0,
        )
        return 3

    print(
        f"{_VERIFY_TAG} scope_poll_cycle {status} scopes_listed={scope_count} "
        "(no WS; maintenance/autonomy/dreaming paths exercised per due)"
    )
    _emit_verify_result(ok=True, exit_code=0, elapsed_s=time.perf_counter() - t0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
