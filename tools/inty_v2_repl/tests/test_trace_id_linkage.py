"""Ensure user and assistant transcript rows share the same trace_id per turn."""

from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_repl import orchestrator
from inty_v2_repl.memory_store_registry import get_memory_store
from inty_v2_repl.models import load_transcript
from inty_v2_repl.paths import WorkspacePaths


def _resp_text(content: str) -> SimpleNamespace:
    msg = SimpleNamespace(content=content, tool_calls=[])
    ch = SimpleNamespace(message=msg, finish_reason="stop")
    return SimpleNamespace(choices=[ch], usage=None)


class _FakeCompletionsSingle:
    def create(self, **kwargs: object) -> SimpleNamespace:
        model = str(kwargs["model"])
        if model == "single-model":
            return _resp_text("single-ok")
        raise AssertionError(f"unexpected model: {model}")


class TestTraceIdLinkage(unittest.TestCase):
    def _init_workspace(self, root: Path) -> None:
        paths = WorkspacePaths(root=root)
        paths.identity.write_text("# I\n", encoding="utf-8")
        paths.soul.write_text("# S\n", encoding="utf-8")
        paths.user_md.write_text("# U\n", encoding="utf-8")
        paths.memory_md.write_text("# M\n", encoding="utf-8")
        paths.transcript.write_text("", encoding="utf-8")
        st = get_memory_store(root)
        st.write_document("IDENTITY.md", "# I\n")
        st.write_document("SOUL.md", "# S\n")
        st.write_document("USER.md", "# U\n")
        st.write_document("MEMORY.md", "# M\n")
        st.write_document("transcript.jsonl", "")

    def test_transcript_user_and_assistant_share_turn_trace_id(self) -> None:
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(completions=_FakeCompletionsSingle()),
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_workspace(root)
            with (
                patch.object(orchestrator, "get_client", return_value=fake_client),
                patch.object(
                    orchestrator,
                    "get_client_dual_llm_tool",
                    return_value=fake_client,
                ),
                patch.object(orchestrator, "default_model", return_value="single-model"),
                patch.object(orchestrator, "dual_llm_enabled", return_value=False),
                patch.object(
                    orchestrator,
                    "async_tool_background_enabled",
                    return_value=False,
                ),
                patch.object(
                    orchestrator,
                    "schedule_memory_update_after_turn",
                    return_value=None,
                ),
                patch.object(
                    orchestrator,
                    "build_openai_repl_tools",
                    return_value=[{"type": "function"}],
                ),
            ):
                out = asyncio.run(
                    orchestrator.run_turn(
                        root,
                        "你好",
                    )
                )
            self.assertEqual(out, "single-ok")

            rows = load_transcript(root / "transcript.jsonl")
            self.assertEqual(len(rows), 2)
            self.assertIsNotNone(rows[0].trace_id)
            self.assertEqual(rows[0].trace_id, rows[1].trace_id)


if __name__ == "__main__":
    unittest.main()
