"""Process-local scope inner-tick throttle and tool_bg overlap state (#3255 slice 2)."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from app.core.companion_harness.companion.scope import CompanionScope

_REGISTRY_GUARD = threading.Lock()
_SCOPE_INNER_TICK_STATE: dict[str, ScopeInnerTickState] = {}


@dataclass
class ScopeInnerTickState:
    """Per-scope maintenance/autonomy throttle and tool_bg overlap (no presence required)."""

    maintenance_fired_monotonic: float | None = None
    maintenance_fired_line_count: int | None = None
    autonomy_fired_monotonic: float | None = None
    autonomy_fired_line_count: int | None = None
    _maintenance_tool_bg_idle: threading.Event | None = field(
        default=None, repr=False
    )
    _autonomy_tool_bg_idle: threading.Event | None = field(
        default=None, repr=False
    )

    def last_maintenance_inner_tick_monotonic(self) -> float | None:
        return self.maintenance_fired_monotonic

    def last_maintenance_transcript_line_count(self) -> int | None:
        return self.maintenance_fired_line_count

    def mark_maintenance_inner_tick_fired(
        self,
        monotonic_time: float,
        transcript_line_count: int,
    ) -> None:
        self.maintenance_fired_monotonic = monotonic_time
        self.maintenance_fired_line_count = transcript_line_count

    def bind_maintenance_tool_bg_idle(self, ev: threading.Event | None) -> None:
        self._maintenance_tool_bg_idle = ev

    def clear_maintenance_tool_bg_idle_if_idle(self) -> None:
        idle_ev = self._maintenance_tool_bg_idle
        if idle_ev is not None and idle_ev.is_set():
            self._maintenance_tool_bg_idle = None

    def maintenance_tool_bg_still_running(self) -> bool:
        idle_ev = self._maintenance_tool_bg_idle
        return idle_ev is not None and (not idle_ev.is_set())

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

    def bind_autonomy_tool_bg_idle(self, ev: threading.Event | None) -> None:
        self._autonomy_tool_bg_idle = ev

    def clear_autonomy_tool_bg_idle_if_idle(self) -> None:
        idle_ev = self._autonomy_tool_bg_idle
        if idle_ev is not None and idle_ev.is_set():
            self._autonomy_tool_bg_idle = None

    def autonomy_tool_bg_still_running(self) -> bool:
        idle_ev = self._autonomy_tool_bg_idle
        return idle_ev is not None and (not idle_ev.is_set())


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
