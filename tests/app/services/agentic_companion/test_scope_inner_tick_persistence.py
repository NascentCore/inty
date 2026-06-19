"""Tests for scope inner-tick Postgres persistence boundary."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.core.companion_harness.companion.scope import CompanionScope
from app.services.agentic_companion.scope_inner_tick_persistence import (
    fetch_initialized_companion_scopes,
)


@pytest.mark.asyncio
async def test_fetch_initialized_companion_scopes_filters_inactive_bonds() -> None:
    active = CompanionScope("user-active", "agent-active", "chat-active")
    inactive = CompanionScope("user-old", "agent-old", "chat-old")
    with patch(
        "app.services.agentic_companion.scope_inner_tick_persistence.list_companion_memory_scopes",
        new_callable=AsyncMock,
        return_value=[active, inactive],
    ):
        with patch(
            "app.services.agentic_companion.scope_inner_tick_persistence.list_active_companion_agent_scope_keys",
            new_callable=AsyncMock,
            return_value=frozenset({("user-active", "agent-active")}),
        ):
            scopes = await fetch_initialized_companion_scopes()
    assert scopes == [active]
