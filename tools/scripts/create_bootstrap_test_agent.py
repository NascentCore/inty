#!/usr/bin/env python3
"""Create a fresh PRIVATE Ops agent for interactive bootstrap testing.

Assumes local Ops is already listening (default ``http://127.0.0.1:8001``).
Bearer: ``.inty_ops_bearer_token`` from ``backend/ops/start.sh --local``.

Run with shell cwd = repository root.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from typing import Any, TextIO

_TAG = "[create-bootstrap-test-agent]"


def _read_bearer_token(token_path: str, stderr: TextIO) -> str | None:
    try:
        with open(token_path, encoding="utf-8") as f:
            raw = f.read()
    except OSError as exc:
        print(
            f"error: cannot read token file {token_path!r}: {exc}", file=stderr
        )
        return None
    tok = raw.strip()
    if not tok:
        print(f"error: token file is empty: {token_path!r}", file=stderr)
        return None
    return tok


def run_create(
    *,
    api_base: str,
    token_path: str,
    http_timeout: float,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    """POST /api/v1/ai/agents; print agent id and REPL hint. Returns 0 on success."""
    tok = _read_bearer_token(token_path, stderr)
    if tok is None:
        return 1

    base = api_base.rstrip("/")
    url = f"{base}/api/v1/ai/agents"
    tag = uuid.uuid4().hex[:10]
    body: dict[str, Any] = {
        "name": f"bootstrap-test-{tag}",
        "gender": "FEMALE",
        "visibility": "PRIVATE",
        "intro": "Bootstrap process test agent.",
        "opening": "Hello.",
        "personality": "Warm, curious.",
        "scenario": "Interactive bootstrap testing.",
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {tok}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=http_timeout) as resp:
            out_any: Any = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")[:800]
        print(f"HTTP {e.code}: {raw}", file=stderr)
        return 1
    except urllib.error.URLError as e:
        print(
            f"error: request failed (is Ops listening on {base!r}?): {e}",
            file=stderr,
        )
        return 1
    except json.JSONDecodeError as e:
        print(f"error: invalid JSON response: {e}", file=stderr)
        return 1

    if not isinstance(out_any, dict):
        print("error: response root is not a JSON object", file=stderr)
        return 1

    out: dict[str, Any] = out_any
    if out.get("code") != 200:
        msg = out.get("message", "")
        data = out.get("data")
        extra = ""
        if isinstance(data, dict):
            ec = data.get("error_code")
            if ec:
                extra = f" error_code={ec!r}"
            lim = data.get("limit")
            used = data.get("used_count")
            if lim is not None:
                extra += f" used_count={used!r} limit={lim!r}"
        print(f"API error code={out.get('code')}: {msg!r}{extra}", file=stderr)
        return 1

    data = out.get("data")
    if not isinstance(data, dict):
        print(f"error: unexpected response: {out!r}", file=stderr)
        return 1
    if not data.get("id"):
        print(f"error: unexpected response: {out!r}", file=stderr)
        return 1

    agent_id = str(data["id"])
    name = str(data.get("name") or body["name"])
    print(f"{_TAG} agent_id={agent_id}", file=stdout)
    print(f"{_TAG} name={name}", file=stdout)
    print(f"{_TAG} api_base={base}", file=stdout)
    print(
        f"{_TAG} repl_command=python -m tools.inty_v2_repl.main repl "
        f"--api-base-url {base} --agent-id {agent_id}",
        file=stdout,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    default_api = (
        os.environ.get("INTY_API_BASE_URL") or ""
    ).strip() or "http://127.0.0.1:8001"
    default_token = (
        os.environ.get("INTY_OPS_BEARER_TOKEN_FILE") or ""
    ).strip() or ".inty_ops_bearer_token"

    p = argparse.ArgumentParser(
        description="Create a PRIVATE agent on local Ops for bootstrap testing."
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
            "Bearer token file (default: $INTY_OPS_BEARER_TOKEN_FILE or "
            f"{default_token!r}; relative to cwd)"
        ),
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="HTTP timeout seconds (default 60)",
    )
    args = p.parse_args(argv)

    timeout = float(args.timeout)
    if timeout <= 0:
        print("error: --timeout must be positive", file=sys.stderr)
        return 1

    return run_create(
        api_base=str(args.api_base).strip(),
        token_path=str(args.token_file).strip(),
        http_timeout=timeout,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )


if __name__ == "__main__":
    raise SystemExit(main())
