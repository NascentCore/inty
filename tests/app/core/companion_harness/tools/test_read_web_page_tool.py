from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.tools.read_web_page import (
    run_read_web_page_sync,
)

_HTML = """<!DOCTYPE html>
<html><head><title>Example Article</title></head>
<body><main>
<p>First paragraph about alpha topics.</p>
<p>Second paragraph covers beta details and more context.</p>
<p>Third paragraph concludes with gamma insights.</p>
</main></body></html>
"""


def test_run_read_web_page_writes_memory_and_returns_markdown(
    tmp_path: Path,
) -> None:
    sc = CompanionScope("rwp", "a", tmp_path.name)
    store = MemoryStore(scope=sc, repository=None)

    mock_resp = MagicMock()
    mock_resp.content = _HTML.encode("utf-8")
    mock_resp.encoding = "utf-8"
    mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
    mock_resp.raise_for_status = MagicMock()

    with patch(
        "app.core.companion_harness.tools.read_web_page.requests.get",
        return_value=mock_resp,
    ):
        out = run_read_web_page_sync(
            store,
            url="https://example.com/page",
            max_bullets=5,
        )

    assert not out.startswith("ERROR:")
    assert "# Example Article" in out
    assert "- " in out
    assert DEFAULT_MEMORY_STORE_SCOPE_PATHS.memory_md in out

    mem = store.read_document_if_exists(DEFAULT_MEMORY_STORE_SCOPE_PATHS.memory_md)
    assert mem is not None
    assert "read_web_page" in mem
    assert "https://example.com/page" in mem
    assert "Takeaways" in mem


def test_run_read_web_page_rejects_localhost(tmp_path: Path) -> None:
    sc = CompanionScope("rwp", "a", f"{tmp_path.name}-loc")
    store = MemoryStore(scope=sc, repository=None)
    out = run_read_web_page_sync(store, url="http://127.0.0.1:8080/secret")
    assert out.startswith("ERROR:")
    assert "local" in out.lower()
