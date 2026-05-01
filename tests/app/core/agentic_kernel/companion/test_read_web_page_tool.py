from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from app.core.agentic_kernel.companion.memory_registry import get_memory_store
from app.core.agentic_kernel.companion.read_web_page import run_read_web_page_sync

_HTML = """<!DOCTYPE html>
<html><head><title>Example Article</title></head>
<body><main>
<p>First paragraph about alpha topics.</p>
<p>Second paragraph covers beta details and more context.</p>
<p>Third paragraph concludes with gamma insights.</p>
</main></body></html>
"""


def test_run_read_web_page_writes_memory_and_returns_markdown(tmp_path: Path) -> None:
    root = tmp_path
    get_memory_store(root)

    mock_resp = MagicMock()
    mock_resp.content = _HTML.encode("utf-8")
    mock_resp.encoding = "utf-8"
    mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
    mock_resp.raise_for_status = MagicMock()

    with patch(
        "app.core.agentic_kernel.companion.read_web_page.requests.get",
        return_value=mock_resp,
    ):
        out = run_read_web_page_sync(
            root,
            url="https://example.com/page",
            max_bullets=5,
        )

    assert not out.startswith("ERROR:")
    assert "# Example Article" in out
    assert "- " in out
    assert "MEMORY.md" in out

    mem = get_memory_store(root).read_document_if_exists("MEMORY.md")
    assert mem is not None
    assert "read_web_page" in mem
    assert "https://example.com/page" in mem
    assert "Takeaways" in mem


def test_run_read_web_page_rejects_localhost(tmp_path: Path) -> None:
    root = tmp_path
    get_memory_store(root)
    out = run_read_web_page_sync(root, url="http://127.0.0.1:8080/secret")
    assert out.startswith("ERROR:")
    assert "local" in out.lower()
