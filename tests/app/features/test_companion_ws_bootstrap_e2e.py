"""
E2E: first ``/api/v1/chat/ws`` connection with ``agent_id`` receives USER_INTERACTIVE bootstrap kickoff.

Requires PostgreSQL reachable at 127.0.0.1:5432 with migrations applied (same as CI ``devops/config.yaml.test``).
Subprocess loads that YAML via ``INTY_CONFIG_YAML``; the pytest process does not.

Enable with ``INTY_COMPANION_WS_BOOTSTRAP_E2E=1``. Calls the real chat model from test config (network).

The subprocess sets ``INTY_E2E_RELAX_SUBSCRIPTION=1`` so guest chat limits do not block kickoff under ``debug: true``.

Optional: ``INTY_COMPANION_WS_BOOTSTRAP_SERVER_STDERR=1`` inherits uvicorn stderr; ``INTY_COMPANION_WS_BOOTSTRAP_RECV_TIMEOUT`` overrides wait seconds.

Marked ``noci`` and gated so default ``pytest`` does not hit OpenRouter.
"""

from __future__ import annotations

import os

import pytest

from tests.support.companion_ws_bootstrap.constants import (
    DEFAULT_RECV_TIMEOUT_SEC,
    ENV_GATE_COMPANION_WS_BOOTSTRAP_E2E,
)
from tests.support.companion_ws_bootstrap.server import (
    postgres_tcp_reachable,
    run_inty_backend_subprocess,
)
from tests.support.companion_ws_bootstrap.ws_client import (
    connect_and_expect_bootstrap_kickoff,
)
from tests.app.api.test_client import TestClient


def _recv_timeout_sec() -> float:
    raw = os.environ.get("INTY_COMPANION_WS_BOOTSTRAP_RECV_TIMEOUT", "").strip()
    if not raw:
        return DEFAULT_RECV_TIMEOUT_SEC
    return float(raw)


@pytest.fixture
def running_inty_backend():
    if os.environ.get(ENV_GATE_COMPANION_WS_BOOTSTRAP_E2E) != "1":
        pytest.skip(
            f"Set {ENV_GATE_COMPANION_WS_BOOTSTRAP_E2E}=1 to run companion WS bootstrap E2E"
        )
    if not postgres_tcp_reachable():
        pytest.skip("PostgreSQL not reachable at 127.0.0.1:5432")
    with run_inty_backend_subprocess() as ctx:
        yield ctx


@pytest.fixture
def bootstrap_e2e_client(running_inty_backend):
    client = TestClient(running_inty_backend.base_url)
    client.create_user()
    try:
        yield client
    finally:
        client.delete_user()
        client.close()


@pytest.mark.noci
@pytest.mark.slow
@pytest.mark.asyncio
async def test_ws_receives_interactive_bootstrap_kickoff(bootstrap_e2e_client):
    agent_id = bootstrap_e2e_client.create_agent()
    token = bootstrap_e2e_client.token
    assert token
    await connect_and_expect_bootstrap_kickoff(
        http_base_url=bootstrap_e2e_client.base_url,
        bearer_token=token,
        agent_id=agent_id,
        recv_timeout_sec=_recv_timeout_sec(),
    )
