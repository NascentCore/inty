"""Smoke tests for companion google_web_search tool module."""

from __future__ import annotations


def test_google_web_search_module_imports() -> None:
    from app.core.companion_harness.tools import google_web_search

    assert callable(google_web_search.run_google_web_search)
