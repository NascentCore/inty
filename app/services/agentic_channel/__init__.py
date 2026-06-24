"""Agent-channel service: multi-medium endpoints, runtime, turns, and presence.

Channel onboard and companion turns key off ``user_id`` / ``agent_id``. Legacy
``readable_id`` is maintenance-mode only — do not reference it in this package.

Import ``ChannelKind`` from ``companion.runtime_channel``. Transport adapters live
under ``adapters/`` (telegram, weixin, app_ws, sms).
"""
