"""needs_startup_profile_inquiry：空 transcript + 占位 IDENTITY/USER 时为 True。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.bootstrap import init_workspace
from inty_v2_text_chat_prototype.memory_store_registry import shutdown_memory_store
from inty_v2_text_chat_prototype.models import load_transcript
from inty_v2_text_chat_prototype.orchestrator import needs_startup_profile_inquiry
from inty_v2_text_chat_prototype.paths import WorkspacePaths


class TestStartupProfileInquiry(unittest.TestCase):
    def test_init_workspace_template_empty_transcript_true(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            init_workspace(root)
            self.assertTrue(needs_startup_profile_inquiry(root))
            shutdown_memory_store(root, timeout_s=2.0)

    def test_system_only_transcript_still_startup_true(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            init_workspace(root)
            paths = WorkspacePaths(root=root)
            paths.transcript.write_text(
                '{"role":"system","content":"对话记录文件创建","ts":"2026-01-01T00:00:00+00:00"}\n',
                encoding="utf-8",
            )
            self.assertTrue(needs_startup_profile_inquiry(root))
            rows = load_transcript(paths.transcript)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].role, "system")
            shutdown_memory_store(root, timeout_s=2.0)

    def test_after_one_turn_transcript_false(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            init_workspace(root)
            paths = WorkspacePaths(root=root)
            paths.transcript.write_text(
                '{"role":"user","content":"hi","ts":"t1"}\n',
                encoding="utf-8",
            )
            self.assertFalse(needs_startup_profile_inquiry(root))
            shutdown_memory_store(root, timeout_s=2.0)

    def test_custom_identity_user_no_markers_false(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            init_workspace(root)
            paths = WorkspacePaths(root=root)
            paths.identity.write_text(
                "# IDENTITY\n\n助手名为小岚，与用户为一对一伴侣关系。\n",
                encoding="utf-8",
            )
            paths.user_md.write_text(
                "# USER\n\n用户希望被称为老林；工作日晚间在线。\n",
                encoding="utf-8",
            )
            self.assertFalse(needs_startup_profile_inquiry(root))
            shutdown_memory_store(root, timeout_s=2.0)


if __name__ == "__main__":
    unittest.main()
