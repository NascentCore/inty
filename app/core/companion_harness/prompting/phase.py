"""Compose phase within a companion turn track (bootstrap vs settled)."""

from __future__ import annotations

from enum import StrEnum

from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    ContextMeta,
)


class Phase(StrEnum):
    """Phase within a user-visible track (e.g. bootstrap vs settled on user_turn)."""

    SETTLED = "settled"
    BOOTSTRAP = "bootstrap"


def resolve_compose_phase(context: ContextMeta) -> Phase:
    """Map context.json bootstrap completion to compose phase."""
    if not context.workspace_bootstrap_user_interactive_completed:
        return Phase.BOOTSTRAP
    return Phase.SETTLED


def resolve_phase_for_compose(
    track: CompanionTurnTrack,
    context_meta: ContextMeta,
) -> Phase:
    """Derive compose phase from track plus context when track does not pin phase."""
    match track:
        case CompanionTurnTrack.USER_CHAT_BOOTSTRAP:
            return Phase.BOOTSTRAP
        case _:
            return resolve_compose_phase(context_meta)
