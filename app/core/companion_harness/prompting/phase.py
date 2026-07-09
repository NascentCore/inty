"""Compose phase within a companion turn track (bootstrap vs settled).

Generated entirely by Cursor agent.
"""

from __future__ import annotations

from enum import StrEnum

from app.core.companion_harness.companion.models import ContextMeta


class Phase(StrEnum):
    """Phase within a user-visible track (e.g. bootstrap vs settled on user_turn)."""

    SETTLED = "settled"
    BOOTSTRAP = "bootstrap"


def resolve_compose_phase(context: ContextMeta) -> Phase:
    """Map context.json bootstrap completion to compose phase."""
    if not context.workspace_bootstrap_user_interactive_completed:
        return Phase.BOOTSTRAP
    return Phase.SETTLED
