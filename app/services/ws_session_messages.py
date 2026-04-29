"""Queue-centric WebSocket session types for ``/api/v1/chat/ws`` (inty-ws only).

Outbound payloads are exact dicts accepted by ``WebSocket.send_json`` for this route.
"""

from __future__ import annotations

from typing import Any, TypeAlias

WsOutboundPayload: TypeAlias = dict[str, Any]
