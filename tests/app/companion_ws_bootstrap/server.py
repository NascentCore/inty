"""Launch Inty via uvicorn in a subprocess on a loopback port for WS bootstrap E2E."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import httpx

from tests.app.companion_ws_bootstrap.constants import (
    DEFAULT_PG_HOST,
    DEFAULT_PG_PORT,
    ENV_E2E_RELAX_SUBSCRIPTION,
    ENV_INTY_CONFIG_YAML,
    ENV_SERVER_STDERR_INHERIT,
    POLL_INTERVAL_SEC,
    SERVER_READY_TIMEOUT_SEC,
    inty_config_yaml_path,
)


@dataclass(frozen=True, slots=True)
class IntySubprocessContext:
    """Handle for a uvicorn child started with ``INTY_CONFIG_YAML``."""

    base_url: str
    process: subprocess.Popen
    config_path: Path


def require_inty_config_yaml() -> Path:
    """Require ``INTY_CONFIG_YAML`` in the environment; validate the file exists."""
    cfg = inty_config_yaml_path()
    if cfg is None:
        raise RuntimeError(
            f"Set {ENV_INTY_CONFIG_YAML} before running companion WS E2E"
        )
    if not cfg.is_file():
        raise FileNotFoundError(f"{ENV_INTY_CONFIG_YAML}={cfg} is not a file")
    return cfg


def postgres_tcp_reachable(
    *,
    host: str = DEFAULT_PG_HOST,
    port: int = DEFAULT_PG_PORT,
    timeout_sec: float = 2.0,
) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_sec):
            return True
    except OSError:
        return False


def allocate_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def wait_http_ready(base_url: str, *, timeout_sec: float) -> None:
    base = base_url.rstrip("/")
    deadline = time.monotonic() + timeout_sec
    last_exc: BaseException | None = None
    while time.monotonic() < deadline:
        try:
            httpx.get(f"{base}/", timeout=2.0)
            return
        except (httpx.ConnectError, httpx.TimeoutException, OSError) as e:
            last_exc = e
        time.sleep(POLL_INTERVAL_SEC)
    raise TimeoutError(
        f"server not reachable at {base_url!r} within {timeout_sec}s (last_err={last_exc!r})"
    )


@contextmanager
def run_inty_backend_subprocess(
    *,
    port: int | None = None,
) -> Iterator[IntySubprocessContext]:
    """Start ``uvicorn backend.inty.main:app``; child inherits ``INTY_CONFIG_YAML``.

    Assumes pytest is invoked from the repository root with ``INTY_CONFIG_YAML`` exported.
    """
    cfg = require_inty_config_yaml()
    bind_port = port if port is not None else allocate_loopback_port()
    base_url = f"http://127.0.0.1:{bind_port}"
    env = os.environ.copy()
    repo = os.getcwd()
    prev_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = repo if not prev_pp else f"{repo}{os.pathsep}{prev_pp}"
    # Guest limits apply when environment=test and debug=true unless subscription bypass sees this flag.
    env[ENV_E2E_RELAX_SUBSCRIPTION] = "1"
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.inty.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(bind_port),
    ]
    inherit_stderr = os.environ.get(ENV_SERVER_STDERR_INHERIT, "").strip() in (
        "1",
        "inherit",
        "yes",
        "true",
    )
    proc = subprocess.Popen(
        cmd,
        cwd=repo,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=None if inherit_stderr else subprocess.DEVNULL,
        text=True,
    )
    try:
        try:
            wait_http_ready(base_url, timeout_sec=SERVER_READY_TIMEOUT_SEC)
        except TimeoutError as exc:
            raise TimeoutError(
                f"{exc}; set {ENV_SERVER_STDERR_INHERIT}=1 to inherit uvicorn stderr for diagnosis."
            ) from exc
        yield IntySubprocessContext(
            base_url=base_url, process=proc, config_path=cfg
        )
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
