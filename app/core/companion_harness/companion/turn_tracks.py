"""Per-track entry aliases; implementations live in ``turn``.

TODO(cleanup): Remove this, callers import the source modules directly.


TODO(companion-package-reorg): Move this module into a focused sub-package under companion_harness (see issue body for draft layout).
https://github.com/NascentCore/inty/issues/3409"""

from __future__ import annotations

from .models import CompanionTurnTrack
from .turn_deps import CompanionTurnDeps
from .turn import (
    run_companion_implicit_sign_on_greeting_turn,
    run_companion_inner_tick_maintenance_turn,
    run_companion_inner_tick_proactive_chat_turn,
    run_companion_inner_tick_scheduled_turn,
    run_companion_user_chat_turn,
    run_inner_tick_autonomy,
)

__all__ = [
    "CompanionTurnDeps",
    "CompanionTurnTrack",
    "run_companion_implicit_sign_on_greeting_turn",
    "run_companion_inner_tick_maintenance_turn",
    "run_companion_inner_tick_proactive_chat_turn",
    "run_companion_inner_tick_scheduled_turn",
    "run_companion_user_chat_turn",
    "run_inner_tick_autonomy",
]
