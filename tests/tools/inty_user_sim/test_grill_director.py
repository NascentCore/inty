"""Unit tests for GrillDirector state machine."""

from __future__ import annotations

from tools.inty_user_sim.director import GrillDirector, absence_schedule
from tools.inty_user_sim.types import (
    GrillObjective,
    GrillPhase,
    SimRunCheckpoint,
)


def _checkpoint(phase: GrillPhase = GrillPhase.BOOTSTRAP) -> SimRunCheckpoint:
    return SimRunCheckpoint(
        run_id="r1",
        agent_id="a1",
        sim_day=0,
        phase=phase,
        director_cursor=0,
        director_seed=42,
        persona_hash="abc",
        turn_count=0,
        rupture_sent=False,
        absence_done_days=[],
    )


def test_bootstrap_objective_sequence() -> None:
    director = GrillDirector(
        phase=GrillPhase.BOOTSTRAP,
        director_seed=1,
        sim_days=14,
    )
    cp = _checkpoint()
    d1 = director.next_directive(0, cp, bootstrap_complete=False)
    assert d1.objective == GrillObjective.BOOTSTRAP_IDENTITY
    cp.director_cursor = 1
    d2 = director.next_directive(0, cp, bootstrap_complete=False)
    assert d2.objective == GrillObjective.BOOTSTRAP_RELATIONSHIP


def test_daily_chat_after_bootstrap() -> None:
    director = GrillDirector(
        phase=GrillPhase.BOOTSTRAP,
        director_seed=1,
        sim_days=14,
    )
    d = director.next_directive(3, _checkpoint(), bootstrap_complete=True)
    assert d.phase == GrillPhase.DAILY_CHAT


def test_absence_schedule_includes_day_7_for_14_days() -> None:
    assert 7 in absence_schedule(14)


def test_absence_directive_on_scheduled_day() -> None:
    director = GrillDirector(
        phase=GrillPhase.DAILY_CHAT,
        director_seed=1,
        sim_days=14,
    )
    d = director.next_directive(7, _checkpoint(GrillPhase.DAILY_CHAT), bootstrap_complete=True)
    assert d.phase == GrillPhase.ABSENCE
    assert d.objective == GrillObjective.WAIT_PROACTIVE


def test_rupture_day_emits_rupture_then_repair_only() -> None:
    director = GrillDirector(
        phase=GrillPhase.DAILY_CHAT,
        director_seed=1,
        sim_days=42,
    )
    cp = _checkpoint(GrillPhase.DAILY_CHAT)
    d1 = director.next_directive(14, cp, bootstrap_complete=True)
    assert d1.objective == GrillObjective.RUPTURE
    d2 = director.next_directive(14, cp, bootstrap_complete=True)
    assert d2.objective == GrillObjective.REPAIR
    d3 = director.next_directive(14, cp, bootstrap_complete=True)
    assert d3.objective == GrillObjective.REPAIR
