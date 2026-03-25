"""Clamp wall-clock sleep used when multiplexing stdin with timers (e.g. heartbeat)."""


def clamp_sleep_seconds(
    seconds: float,
    *,
    min_seconds: float,
    max_seconds: float,
) -> float:
    """
    Return a positive duration in [min_seconds, max_seconds] suitable for queue.get(timeout=...).

    Typical use: `wait` from a schedule may be huge; cap per poll so the loop can react to new stdin lines.
    """
    if min_seconds <= 0:
        raise ValueError("min_seconds must be positive")
    if max_seconds < min_seconds:
        raise ValueError("max_seconds must be >= min_seconds")
    s = max(min_seconds, seconds)
    return min(s, max_seconds)
