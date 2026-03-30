"""google_web_search tool: env validation and Google CSE response formatting."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.workspace_init_tools import execute_tool_call_blocking


class TestGoogleWebSearchTool(unittest.TestCase):
    def test_empty_query_errors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = execute_tool_call_blocking(
                root,
                "google_web_search",
                json.dumps({"query": "   "}),
            )
            self.assertTrue(out.startswith("ERROR:"))

    def test_missing_env_errors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env = {
                k: v
                for k, v in os.environ.items()
                if k not in ("GOOGLE_CSE_API_KEY", "GOOGLE_CSE_ID")
            }
            with patch.dict(os.environ, env, clear=True):
                out = execute_tool_call_blocking(
                    root,
                    "google_web_search",
                    json.dumps({"query": "hello"}),
                )
            self.assertIn("GOOGLE_CSE_API_KEY", out)
            self.assertTrue(out.startswith("ERROR:"))

    def test_success_formats_items(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "{}"
        mock_resp.json.return_value = {
            "items": [
                {
                    "title": "Example",
                    "link": "https://example.com/page",
                    "snippet": "A short snippet.",
                }
            ]
        }
        client = MagicMock()
        client.get = AsyncMock(return_value=mock_resp)
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=client)
        cm.__aexit__ = AsyncMock(return_value=None)

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch.dict(
                os.environ,
                {"GOOGLE_CSE_API_KEY": "k", "GOOGLE_CSE_ID": "cx"},
            ):
                with patch(
                    "inty_v2_text_chat_prototype.google_web_search.httpx.AsyncClient",
                    return_value=cm,
                ):
                    out = execute_tool_call_blocking(
                        root,
                        "google_web_search",
                        json.dumps({"query": "test query"}),
                    )
        self.assertIn("Example", out)
        self.assertIn("https://example.com/page", out)
        self.assertIn("A short snippet.", out)
        self.assertFalse(out.startswith("ERROR:"))

    def test_http_error_string(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.text = "forbidden"
        client = MagicMock()
        client.get = AsyncMock(return_value=mock_resp)
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=client)
        cm.__aexit__ = AsyncMock(return_value=None)

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch.dict(
                os.environ,
                {"GOOGLE_CSE_API_KEY": "k", "GOOGLE_CSE_ID": "cx"},
            ):
                with patch(
                    "inty_v2_text_chat_prototype.google_web_search.httpx.AsyncClient",
                    return_value=cm,
                ):
                    out = execute_tool_call_blocking(
                        root,
                        "google_web_search",
                        json.dumps({"query": "x"}),
                    )
        self.assertTrue(out.startswith("ERROR:"))
        self.assertIn("403", out)

    def test_no_items_returns_placeholder(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"items": []}
        client = MagicMock()
        client.get = AsyncMock(return_value=mock_resp)
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=client)
        cm.__aexit__ = AsyncMock(return_value=None)

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch.dict(
                os.environ,
                {"GOOGLE_CSE_API_KEY": "k", "GOOGLE_CSE_ID": "cx"},
            ):
                with patch(
                    "inty_v2_text_chat_prototype.google_web_search.httpx.AsyncClient",
                    return_value=cm,
                ):
                    out = execute_tool_call_blocking(
                        root,
                        "google_web_search",
                        json.dumps({"query": "zzzznomatch12345"}),
                    )
        self.assertEqual(out, "(no results)")


if __name__ == "__main__":
    unittest.main()
