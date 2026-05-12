#!/usr/bin/env python3
"""List AI agent UUIDs and names from local Ops ``GET /api/v1/ai/agents/admin/list``.

Requires a **superuser** bearer token (e.g. ``user-testing`` JWT written by
``backend/ops/start.sh --local`` to ``.inty_ops_bearer_token`` at repo root).

Run with **shell cwd = repository root** so relative ``--token-file`` /
``.inty_ops_bearer_token`` resolve correctly. Uses stdlib only (no ``PYTHONPATH``).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, TextIO


def _read_bearer_token(token_path: str) -> str | None:
    try:
        with open(token_path, encoding="utf-8") as f:
            raw = f.read()
    except OSError as exc:
        print(f"error: cannot read token file {token_path!r}: {exc}", file=sys.stderr)
        return None
    tok = raw.strip()
    if not tok:
        print(f"error: token file is empty: {token_path!r}", file=sys.stderr)
        return None
    return tok


def _print_empty_guidance(api_base: str, out: TextIO) -> None:
    print(
        "admin/list returned no agents. Create one, then re-run:",
        "python3 scripts/inty_backend_smoke_tests/test_chat_ws.py \\",
        f"  --api-base {api_base} --create-agent",
        sep="\n",
        file=out,
    )


def run_list(
    *,
    api_base: str,
    token_path: str,
    limit: int,
    timeout: float,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    """Fetch admin agent list; print ``id<TAB>name`` lines or empty-db guidance.

    Returns 0 on success (including empty list with guidance). Returns 1 on
    transport/parse/auth errors.
    """
    tok = _read_bearer_token(token_path)
    if tok is None:
        return 1

    base = api_base.rstrip("/")
    url = f"{base}/api/v1/ai/agents/admin/list?limit={limit}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {tok}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body_any: Any = json.load(resp)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")[:800]
        print(f"HTTP {e.code}: {raw}", file=stderr)
        return 1
    except urllib.error.URLError as e:
        print(
            f"error: request failed (is Ops listening? correct --api-base?): {e}",
            file=stderr,
        )
        return 1
    except json.JSONDecodeError as e:
        print(f"error: invalid JSON response: {e}", file=stderr)
        return 1

    if not isinstance(body_any, dict):
        print("error: response root is not a JSON object", file=stderr)
        return 1

    body: dict[str, Any] = body_any
    api_code = body.get("code", 200)
    if api_code != 200:
        msg = body.get("message", "")
        print(f"API error code={api_code}: {msg}", file=stderr)
        return 1

    data = body.get("data")
    if data is None:
        rows: list[Any] = []
    elif isinstance(data, list):
        rows = data
    else:
        print("error: response data is not a list", file=stderr)
        return 1

    if not rows:
        _print_empty_guidance(base, stdout)
        return 0

    for a in rows:
        if not isinstance(a, dict):
            print("error: agent entry is not an object", file=stderr)
            return 1
        print(str(a.get("id", "")), str(a.get("name", "")), sep="\t", file=stdout)
    return 0


def main(argv: list[str] | None = None) -> int:
    default_api = (
        (os.environ.get("INTY_API_BASE_URL") or "").strip()
        or "http://127.0.0.1:8001"
    )
    default_token = (
        (os.environ.get("INTY_OPS_BEARER_TOKEN_FILE") or "").strip()
        or ".inty_ops_bearer_token"
    )

    p = argparse.ArgumentParser(
        description=(
            "Print agent id and name (tab-separated) from Ops admin list endpoint."
        )
    )
    p.add_argument(
        "--api-base",
        default=default_api,
        help=f"Ops HTTP base URL (default: $INTY_API_BASE_URL or {default_api!r})",
    )
    p.add_argument(
        "--token-file",
        default=default_token,
        help=(
            "Path to bearer token file (default: $INTY_OPS_BEARER_TOKEN_FILE or "
            f"{default_token!r}; relative to cwd)"
        ),
    )
    p.add_argument(
        "--limit",
        type=int,
        default=50,
        help="admin/list limit query param (1..1000, default 50)",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="HTTP timeout seconds (default 60)",
    )
    args = p.parse_args(argv)

    limit = max(1, min(int(args.limit), 1000))
    timeout = float(args.timeout)
    if timeout <= 0:
        print("error: --timeout must be positive", file=sys.stderr)
        return 1

    return run_list(
        api_base=str(args.api_base).strip(),
        token_path=str(args.token_file).strip(),
        limit=limit,
        timeout=timeout,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )


if __name__ == "__main__":
    raise SystemExit(main())
