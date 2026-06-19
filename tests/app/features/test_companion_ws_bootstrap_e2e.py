"""
E2E: ``/api/v1/chat/ws`` greeting via ``user_signed_on`` + ``message_id`` returns assistant JSON.

Requires PostgreSQL reachable at 127.0.0.1:15432 with migrations applied.
Export ``INTY_CONFIG_YAML`` before pytest; the subprocess uvicorn inherits it.

Enable with ``INTY_COMPANION_WS_BOOTSTRAP_E2E=1`` or ``INTY_COMPANION_WS_IMPLICIT_SIGNON_E2E=1``. Calls the real chat model from that config (network).

The subprocess sets ``INTY_E2E_RELAX_SUBSCRIPTION=1`` so guest chat limits do not block under ``debug: true``.

Optional: ``INTY_COMPANION_WS_BOOTSTRAP_SERVER_STDERR=1`` inherits uvicorn stderr; ``INTY_COMPANION_WS_BOOTSTRAP_RECV_TIMEOUT`` overrides wait seconds.

``test_ws_new_agent_first_implicit_sign_on_context_mode_unspecific`` asserts ``meta_data.context_mode`` is ``unspecific`` for a newly created agent on the first implicit sign-on turn.

Marked ``noci`` and gated so default ``pytest`` does not hit OpenRouter.
"""

from __future__ import annotations

import os

import pytest

from tests.app.companion_ws_bootstrap.constants import (
    DEFAULT_RECV_TIMEOUT_SEC,
    ENV_INTY_CONFIG_YAML,
    companion_ws_implicit_e2e_gated,
    inty_config_yaml_path,
)
from tests.app.companion_ws_bootstrap.server import (
    postgres_tcp_reachable,
    run_inty_backend_subprocess,
)
from app.core.companion_harness.experience_profile.context_mode import (
    ExperienceContextMode,
)

from tests.app.companion_ws_bootstrap.ws_client import (
    connect_send_implicit_sign_on_and_expect_assistant,
)
from tests.app.api.test_client import TestClient


def _recv_timeout_sec() -> float:
    raw = os.environ.get("INTY_COMPANION_WS_BOOTSTRAP_RECV_TIMEOUT", "").strip()
    if not raw:
        return DEFAULT_RECV_TIMEOUT_SEC
    return float(raw)


@pytest.fixture
def running_inty_backend():
    if not companion_ws_implicit_e2e_gated():
        pytest.skip(
            "Set INTY_COMPANION_WS_BOOTSTRAP_E2E=1 or INTY_COMPANION_WS_IMPLICIT_SIGNON_E2E=1 "
            "to run companion WS implicit sign-on E2E"
        )
    if not postgres_tcp_reachable():
        pytest.skip("PostgreSQL not reachable at 127.0.0.1:15432")
    if inty_config_yaml_path() is None:
        pytest.skip(
            f"Set {ENV_INTY_CONFIG_YAML} before running companion WS E2E"
        )
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
async def test_ws_implicit_user_signed_on_returns_assistant(
    bootstrap_e2e_client,
):
    agent_id = bootstrap_e2e_client.create_agent()
    token = bootstrap_e2e_client.token
    assert token
    await connect_send_implicit_sign_on_and_expect_assistant(
        http_base_url=bootstrap_e2e_client.base_url,
        bearer_token=token,
        agent_id=agent_id,
        recv_timeout_sec=_recv_timeout_sec(),
        query_agent_id=True,
    )


@pytest.mark.noci
@pytest.mark.slow
@pytest.mark.asyncio
async def test_ws_new_agent_first_implicit_sign_on_context_mode_unspecific(
    bootstrap_e2e_client,
):
    """Fresh POST /ai/agents id + first WS implicit sign-on sees unspecific context_mode in meta."""
    agent_id = bootstrap_e2e_client.create_agent()
    token = bootstrap_e2e_client.token
    assert token
    await connect_send_implicit_sign_on_and_expect_assistant(
        http_base_url=bootstrap_e2e_client.base_url,
        bearer_token=token,
        agent_id=agent_id,
        recv_timeout_sec=_recv_timeout_sec(),
        query_agent_id=True,
        expected_context_mode=ExperienceContextMode.UNSPECIFIC.value,
    )
