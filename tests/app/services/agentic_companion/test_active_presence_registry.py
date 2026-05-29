from __future__ import annotations

from app.services.agentic_companion.active_presence_registry import (
    clear_present,
    is_present,
    mark_present,
)


def test_absent_by_default() -> None:
    assert is_present("u:a:c-absent") is False


def test_mark_then_clear_toggles_presence() -> None:
    key = "u:a:c-toggle"
    mark_present(key)
    assert is_present(key) is True
    clear_present(key)
    assert is_present(key) is False


def test_refcounted_until_last_clear() -> None:
    key = "u:a:c-refcount"
    mark_present(key)
    mark_present(key)
    clear_present(key)
    assert is_present(key) is True
    clear_present(key)
    assert is_present(key) is False
