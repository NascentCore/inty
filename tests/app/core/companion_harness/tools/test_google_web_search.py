"""Import smoke for companion Google web search tool."""

from __future__ import annotations

from app.core.companion_harness.tools import google_web_search


def test_google_web_search_module_imports() -> None:
    assert callable(google_web_search.run_google_web_search)
    assert callable(google_web_search.run_google_web_search_sync)
