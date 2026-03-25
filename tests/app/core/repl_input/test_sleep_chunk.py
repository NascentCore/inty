import pytest

from app.core.repl_input.sleep_chunk import clamp_sleep_seconds


def test_clamp_sleep_seconds_within_bounds() -> None:
    assert clamp_sleep_seconds(1.0, min_seconds=0.05, max_seconds=3600.0) == 1.0


def test_clamp_sleep_seconds_below_min() -> None:
    assert clamp_sleep_seconds(0.01, min_seconds=0.05, max_seconds=3600.0) == 0.05


def test_clamp_sleep_seconds_above_max() -> None:
    assert clamp_sleep_seconds(99999.0, min_seconds=0.05, max_seconds=3600.0) == 3600.0


def test_clamp_sleep_seconds_rejects_bad_bounds() -> None:
    with pytest.raises(ValueError):
        clamp_sleep_seconds(1.0, min_seconds=0.0, max_seconds=1.0)
    with pytest.raises(ValueError):
        clamp_sleep_seconds(1.0, min_seconds=0.1, max_seconds=0.05)
