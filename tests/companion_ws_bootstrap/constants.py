"""Named constants for companion WebSocket implicit sign-on E2E."""

from __future__ import annotations

import os

ENV_GATE_COMPANION_WS_BOOTSTRAP_E2E = "INTY_COMPANION_WS_BOOTSTRAP_E2E"
ENV_GATE_COMPANION_WS_IMPLICIT_SIGNON_E2E = "INTY_COMPANION_WS_IMPLICIT_SIGNON_E2E"
# Child-only: must match app/services/subscription_service.check_chat_limit bypass.
ENV_E2E_RELAX_SUBSCRIPTION = "INTY_E2E_RELAX_SUBSCRIPTION"
ENV_SERVER_STDERR_INHERIT = "INTY_COMPANION_WS_BOOTSTRAP_SERVER_STDERR"
DEFAULT_RECV_TIMEOUT_SEC = 120.0
SERVER_READY_TIMEOUT_SEC = 90.0
POLL_INTERVAL_SEC = 0.5
DEFAULT_PG_HOST = "127.0.0.1"
DEFAULT_PG_PORT = 5432
# Below chat_ws_idle_timeout_seconds so the server keeps reading while waiting for LLM.
WS_KEEPALIVE_PING_INTERVAL_SEC = 25.0


def companion_ws_implicit_e2e_gated() -> bool:
    return (
        os.environ.get(ENV_GATE_COMPANION_WS_BOOTSTRAP_E2E) == "1"
        or os.environ.get(ENV_GATE_COMPANION_WS_IMPLICIT_SIGNON_E2E) == "1"
    )
