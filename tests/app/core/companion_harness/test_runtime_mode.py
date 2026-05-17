"""INTY_RUNTIME_MODE resolution."""

from __future__ import annotations

import pytest

from app.core.companion_harness.runtime_mode import (
    IntyRuntimeMode,
    inty_runtime_mode_is_debug,
    resolve_inty_runtime_mode,
)


def test_runtime_mode_default_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INTY_RUNTIME_MODE", raising=False)
    assert resolve_inty_runtime_mode() is IntyRuntimeMode.DEBUG
    assert inty_runtime_mode_is_debug() is True


def test_runtime_mode_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTY_RUNTIME_MODE", "PROD")
    assert resolve_inty_runtime_mode() is IntyRuntimeMode.PROD
    assert inty_runtime_mode_is_debug() is False


def test_runtime_mode_debug_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTY_RUNTIME_MODE", "debug")
    assert resolve_inty_runtime_mode() is IntyRuntimeMode.DEBUG


def test_runtime_mode_invalid_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTY_RUNTIME_MODE", "staging")
    with pytest.raises(ValueError, match="PROD or DEBUG"):
        resolve_inty_runtime_mode()
