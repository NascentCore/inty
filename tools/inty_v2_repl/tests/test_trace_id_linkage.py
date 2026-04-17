"""Ensure transcript trace_id links to llm_trace rows per turn."""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_repl import orchestrator
from inty_v2_repl.llm_trace import configure_llm_trace_file
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

    def test_transcript_and_llm_trace_share_same_turn_trace_id(self) -> None:
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(completions=_FakeCompletionsSingle()),
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_workspace(root)
            trace_path = root / "llm_trace.jsonl"
            configure_llm_trace_file(trace_path)
            try:
                with (
                    patch.object(orchestrator, "get_client", return_value=fake_client),
                    patch.object(
                        orchestrator,
                        "get_client_dual_llm_tool",
                        return_value=fake_client,
                    ),
                    patch.object(
                        orchestrator, "default_model", return_value="single-model"
                    ),
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
                            llm_trace=True,
                        )
                    )
                self.assertEqual(out, "single-ok")
            finally:
                configure_llm_trace_file(None)

            rows = load_transcript(root / "transcript.jsonl")
            self.assertEqual(len(rows), 2)
            self.assertIsNotNone(rows[0].trace_id)
            self.assertEqual(rows[0].trace_id, rows[1].trace_id)
            turn_trace_id = rows[0].trace_id
            assert turn_trace_id is not None

            trace_rows = [
                json.loads(line)
                for line in trace_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertGreaterEqual(len(trace_rows), 1)
            trace_ids = {str(r.get("trace_id", "")) for r in trace_rows}
            self.assertIn(turn_trace_id, trace_ids)


if __name__ == "__main__":
    unittest.main()
