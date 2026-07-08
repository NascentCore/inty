"""Process-local scope inner-tick throttle state (#3255 slice 2)."""

from __future__ import annotations

import threading
from dataclasses import dataclass

from app.core.companion_harness.companion.scope import CompanionScope

_REGISTRY_GUARD = threading.Lock()
_SCOPE_INNER_TICK_STATE: dict[str, ScopeInnerTickState] = {}


@dataclass
class ScopeInnerTickState:
    """Per-scope monolog/autonomy throttle (no presence required)."""

    monolog_fired_monotonic: float | None = None
    monolog_fired_line_count: int | None = None
    autonomy_fired_monotonic: float | None = None
    autonomy_fired_line_count: int | None = None

    def last_monolog_inner_tick_monotonic(self) -> float | None:
        return self.monolog_fired_monotonic

    def last_monolog_transcript_line_count(self) -> int | None:
        return self.monolog_fired_line_count

    def mark_monolog_inner_tick_fired(
        self,
        monotonic_time: float,
        transcript_line_count: int,
    ) -> None:
        self.monolog_fired_monotonic = monotonic_time
        self.monolog_fired_line_count = transcript_line_count

    def last_autonomy_inner_tick_monotonic(self) -> float | None:
        return self.autonomy_fired_monotonic

    def last_autonomy_transcript_line_count(self) -> int | None:
        return self.autonomy_fired_line_count

    def mark_autonomy_inner_tick_fired(
        self,
        monotonic_time: float,
        transcript_line_count: int,
    ) -> None:
        self.autonomy_fired_monotonic = monotonic_time
        self.autonomy_fired_line_count = transcript_line_count


# TODO(dreaming-completion-notify): #3744 — add per-scope dreaming checkpoint Event +
# last_memory_sequence snapshot for scope worker dreaming completion.
def get_scope_inner_tick_state(scope: CompanionScope) -> ScopeInnerTickState:
    """Return singleton inner-tick state for one companion scope."""
    key = scope.registry_key()
    with _REGISTRY_GUARD:
        existing = _SCOPE_INNER_TICK_STATE.get(key)
        if existing is not None:
            return existing
        state = ScopeInnerTickState()
        _SCOPE_INNER_TICK_STATE[key] = state
        return state


def release_scope_inner_tick_state(scope: CompanionScope) -> None:
    """Drop process-local inner-tick state for a scope (e.g. MemoryStore shutdown)."""
    key = scope.registry_key()
    with _REGISTRY_GUARD:
        _SCOPE_INNER_TICK_STATE.pop(key, None)
