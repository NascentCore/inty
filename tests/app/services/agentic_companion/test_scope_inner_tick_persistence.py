"""Tests for scope inner-tick Postgres persistence boundary."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.core.companion_harness.companion.scope import CompanionScope
from app.services.agentic_companion.scope_inner_tick_persistence import (
    fetch_initialized_companion_scopes,
)


@pytest.mark.asyncio
async def test_fetch_initialized_companion_scopes_delegates_to_listing() -> None:
    expected = [CompanionScope("u", "a", "c")]
    with patch(
        "app.services.agentic_companion.scope_inner_tick_persistence.list_companion_memory_scopes",
        new_callable=AsyncMock,
        return_value=expected,
    ) as listing:
        scopes = await fetch_initialized_companion_scopes()
    assert scopes == expected
    listing.assert_awaited_once()
