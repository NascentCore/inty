"""Agent-channel service: multi-medium endpoints, runtime, turns, and presence.

Channel onboard and companion turns key off ``user_id`` / ``agent_id``. Legacy
``readable_id`` is maintenance-mode only — do not reference it in this package.

TODO(rename-channel-to-gateway): Service-layer gateway runtime; import ``GatewayKind`` from — #3548
``agent_channel/gateway.py``. Rename adapters/ → gateways/ per #3548.
"""
