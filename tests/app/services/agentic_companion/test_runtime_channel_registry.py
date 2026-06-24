"""Tests for active gateway exclusivity registry."""

from __future__ import annotations

from app.core.companion_harness.agent_channel.gateway import GatewayKind
from app.services.agentic_companion.active_gateway_registry import (
    clear_all_for_tests,
    other_active_gateway,
    register_active_gateway,
)


def test_active_gateway_registry_detects_telegram_conflict() -> None:
    clear_all_for_tests()
    user_id = "user-gateway-test"
    register_active_gateway(
        user_id=user_id,
        gateway=GatewayKind.TELEGRAM,
    )
    conflict = other_active_gateway(
        user_id=user_id,
        desired=GatewayKind.APP_WS,
    )
    assert conflict == GatewayKind.TELEGRAM
    clear_all_for_tests()


def test_active_gateway_registry_detects_sms_conflict() -> None:
    clear_all_for_tests()
    user_id = "user-gateway-sms-test"
    register_active_gateway(
        user_id=user_id,
        gateway=GatewayKind.SMS,
    )
    conflict = other_active_gateway(
        user_id=user_id,
        desired=GatewayKind.APP_WS,
    )
    assert conflict == GatewayKind.SMS
    clear_all_for_tests()
