"""Tests for scope-level inner-tick throttle state (#3255 slice 2)."""

from __future__ import annotations

from app.core.companion_harness.companion.scope import CompanionScope
from app.services.agentic_companion.scope_inner_tick_state import (
    get_scope_inner_tick_state,
    release_scope_inner_tick_state,
)


def test_scope_inner_tick_state_throttle() -> None:
    scope = CompanionScope("u", "a", "c")
    state_a = get_scope_inner_tick_state(scope)
    state_b = get_scope_inner_tick_state(scope)
    assert state_a is state_b

    state_a.mark_monolog_inner_tick_fired(100.0, 5)
    assert state_b.last_monolog_inner_tick_monotonic() == 100.0
    assert state_b.last_monolog_transcript_line_count() == 5

    release_scope_inner_tick_state(scope)
    state_c = get_scope_inner_tick_state(scope)
    assert state_c is not state_a
    assert state_c.last_monolog_inner_tick_monotonic() is None
