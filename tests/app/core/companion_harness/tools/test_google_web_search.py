"""Smoke tests for Google Custom Search companion tool."""

from __future__ import annotations

from app.core.companion_harness.tools.google_web_search import (
    run_google_web_search_sync,
)


def test_run_google_web_search_sync_rejects_empty_query() -> None:
    out = run_google_web_search_sync(query="   ", num_results=None)
    assert out.startswith("ERROR:")

