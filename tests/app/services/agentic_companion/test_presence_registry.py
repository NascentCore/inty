"""CompanionPresenceRegistry: one WS holder per (user_id, agent_id)."""

from __future__ import annotations

import pytest

from app.services.agentic_companion.presence_registry import (
    CompanionPresenceRegistry,
    PresenceBusyError,
)


def test_try_register_first_holder_succeeds() -> None:
    registry = CompanionPresenceRegistry()
    registry.try_register("user-1", "agent-a", "ws-conn-1")
    registry.try_register("user-1", "agent-a", "ws-conn-1")


def test_try_register_second_holder_raises_presence_busy() -> None:
    registry = CompanionPresenceRegistry()
    registry.try_register("user-2", "agent-b", "ws-conn-a")
    with pytest.raises(PresenceBusyError) as exc_info:
        registry.try_register("user-2", "agent-b", "ws-conn-b")
    err = exc_info.value
    assert err.lease_key == "user-2:agent-b"
    assert err.incumbent_holder_id == "ws-conn-a"
    assert err.requested_holder_id == "ws-conn-b"


def test_release_allows_new_holder_to_register() -> None:
    registry = CompanionPresenceRegistry()
    registry.try_register("user-3", "agent-c", "ws-conn-first")
    registry.release("user-3", "agent-c", "ws-conn-first")
    registry.try_register("user-3", "agent-c", "ws-conn-second")


def test_release_wrong_holder_does_not_clear_lease() -> None:
    registry = CompanionPresenceRegistry()
    registry.try_register("user-4", "agent-d", "ws-conn-owner")
    registry.release("user-4", "agent-d", "ws-conn-other")
    with pytest.raises(PresenceBusyError):
        registry.try_register("user-4", "agent-d", "ws-conn-intruder")
