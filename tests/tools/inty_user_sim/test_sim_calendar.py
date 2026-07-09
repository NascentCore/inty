"""Unit tests for SimCalendar and WallClockGapPolicy."""

from __future__ import annotations

from datetime import date

from tools.inty_user_sim.types import SimCalendar, WallClockGapPolicy


def test_sim_calendar_advance_and_time_context() -> None:
    cal = SimCalendar(
        sim_start=date(2026, 1, 1),
        sim_now=date(2026, 1, 1),
        minutes_per_sim_day=5.0,
        iana_timezone="Asia/Shanghai",
    )
    cal.advance_sim_days(3)
    assert cal.sim_day_index() == 3
    utc = cal.to_user_time_context()
    assert utc.timezone == "Asia/Shanghai"
    assert "2026-01-04" in utc.local_time


def test_wall_clock_gap_sample() -> None:
    policy = WallClockGapPolicy(
        absence_sim_days_min=3,
        absence_sim_days_max=7,
        wall_seconds_per_sim_day=1.0,
    )
    gap = policy.sample_gap_sim_days(10)
    assert 3 <= gap <= 7
