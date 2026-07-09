"""Tests for track-composed user_turn phase resolution."""

from __future__ import annotations

from app.core.companion_harness.companion.models import ContextMeta
from app.core.companion_harness.prompting.tracks import (
    Phase,
    resolve_compose_phase,
)


def test_resolve_compose_phase_bootstrap_when_incomplete() -> None:
    assert (
        resolve_compose_phase(
            ContextMeta(workspace_bootstrap_user_interactive_completed=False)
        )
        == Phase.BOOTSTRAP
    )


def test_resolve_compose_phase_settled_when_complete() -> None:
    assert (
        resolve_compose_phase(
            ContextMeta(workspace_bootstrap_user_interactive_completed=True)
        )
        == Phase.SETTLED
    )
