"""Public turn-track entry aliases for the companion harness.

WebSocket sessions, managers, and schedulers enter the companion harness through
explicit tracks: user chat, implicit sign-on greeting, proactive inner tick,
scheduled inner tick, and maintenance inner tick. This module keeps those entry
names importable from one place while their implementations stay in the turn
pipeline.
"""

from __future__ import annotations

from .models import CompanionTurnTrack
from .turn import (
    run_companion_implicit_sign_on_greeting_turn,
    run_companion_inner_tick_maintenance_turn,
    run_companion_inner_tick_proactive_chat_turn,
    run_companion_inner_tick_scheduled_turn,
    run_companion_user_chat_turn,
)

__all__ = [
    "CompanionTurnTrack",
    "run_companion_implicit_sign_on_greeting_turn",
    "run_companion_inner_tick_maintenance_turn",
    "run_companion_inner_tick_proactive_chat_turn",
    "run_companion_inner_tick_scheduled_turn",
    "run_companion_user_chat_turn",
]
