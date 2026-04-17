"""google_web_search tool: env validation and Google CSE response formatting."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_repl.memory_store_registry import get_memory_store
from inty_v2_repl.workspace_init_tools import execute_tool_call_blocking


class TestGoogleWebSearchTool(unittest.TestCase):
    def test_schedule_task_success(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = execute_tool_call_blocking(
                root,
                "schedule_task",
                json.dumps(
                    {
                        "exec_time_utc": "2026-04-03T05:30:00+00:00",
                        "task_text": "提醒我出门",
                    },
                    ensure_ascii=False,
                ),
            )
            self.assertTrue(out.startswith("OK scheduled task"))
            body = get_memory_store(root).read_document_if_exists(
                ".companion_schedule_tasks.json"
            )
            self.assertIsNotNone(body)
            loaded = json.loads(body)
            self.assertEqual(len(loaded["tasks"]), 1)
            self.assertEqual(loaded["tasks"][0]["task_text"], "提醒我出门")

    def test_schedule_task_invalid_time_errors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = execute_tool_call_blocking(
                root,
                "schedule_task",
                json.dumps(
                    {
                        "exec_time_utc": "2026-04-03 05:30:00",
                        "task_text": "提醒我出门",
                    },
                    ensure_ascii=False,
                ),
            )
            self.assertTrue(out.startswith("ERROR:"))

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
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch.dict(
                os.environ,
                {"GOOGLE_CSE_API_KEY": "k", "GOOGLE_CSE_ID": "cx"},
            ):
                with patch(
                    "app.core.agentic_kernel.companion.google_web_search.http_get_json",
                    return_value={
                        "items": [
                            {
                                "title": "Example",
                                "link": "https://example.com/page",
                                "snippet": "A short snippet.",
                            }
                        ]
                    },
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
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch.dict(
                os.environ,
                {"GOOGLE_CSE_API_KEY": "k", "GOOGLE_CSE_ID": "cx"},
            ):
                with patch(
                    "app.core.agentic_kernel.companion.google_web_search.http_get_json",
                    side_effect=RuntimeError("403 Client Error: Forbidden for url"),
                ):
                    out = execute_tool_call_blocking(
                        root,
                        "google_web_search",
                        json.dumps({"query": "x"}),
                    )
        self.assertTrue(out.startswith("ERROR:"))
        self.assertIn("403", out)

    def test_no_items_returns_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch.dict(
                os.environ,
                {"GOOGLE_CSE_API_KEY": "k", "GOOGLE_CSE_ID": "cx"},
            ):
                with patch(
                    "app.core.agentic_kernel.companion.google_web_search.http_get_json",
                    return_value={"items": []},
                ):
                    out = execute_tool_call_blocking(
                        root,
                        "google_web_search",
                        json.dumps({"query": "zzzznomatch12345"}),
                    )
        self.assertEqual(out, "(no results)")


if __name__ == "__main__":
    unittest.main()
