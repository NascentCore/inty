"""is_workspace_initialized：与 run_turn 所需五件套一致。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.orchestrator import (
    is_workspace_bootstrap_complete,
    is_workspace_initialized,
    is_workspace_transcript_empty,
    repl_heartbeat_suppressed_for_workspace_bootstrap,
)


def _touch(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("", encoding="utf-8")


class TestIsWorkspaceInitialized(unittest.TestCase):
    def test_empty_dir_false(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir()
            self.assertFalse(is_workspace_initialized(root))

    def test_all_five_true(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir()
            _touch(root / "IDENTITY.md")
            _touch(root / "SOUL.md")
            _touch(root / "USER.md")
            _touch(root / "MEMORY.md")
            _touch(root / "transcript.jsonl")
            self.assertTrue(is_workspace_initialized(root))

    def test_bootstrap_complete_marker(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir()
            self.assertFalse(is_workspace_bootstrap_complete(root))
            _touch(root / "BOOSTRAPED")
            self.assertTrue(is_workspace_bootstrap_complete(root))

    def test_transcript_empty_for_gate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir()
            _touch(root / "transcript.jsonl")
            self.assertTrue(is_workspace_transcript_empty(root))
            (root / "transcript.jsonl").write_text(
                '{"role":"user","content":"hi","ts":"t","uuid":"u"}\n',
                encoding="utf-8",
            )
            self.assertFalse(is_workspace_transcript_empty(root))

    def test_repl_heartbeat_suppressed_during_template_stub_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir()
            (root / "IDENTITY.md").write_text("等待用户定义中\n", encoding="utf-8")
            (root / "USER.md").write_text("待了解\n", encoding="utf-8")
            _touch(root / "SOUL.md")
            _touch(root / "MEMORY.md")
            _touch(root / "transcript.jsonl")
            self.assertTrue(repl_heartbeat_suppressed_for_workspace_bootstrap(root))

    def test_repl_heartbeat_not_suppressed_after_boostraped(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir()
            (root / "IDENTITY.md").write_text("等待用户定义中\n", encoding="utf-8")
            (root / "USER.md").write_text("待了解\n", encoding="utf-8")
            _touch(root / "SOUL.md")
            _touch(root / "MEMORY.md")
            _touch(root / "transcript.jsonl")
            _touch(root / "BOOSTRAPED")
            self.assertFalse(repl_heartbeat_suppressed_for_workspace_bootstrap(root))

    def test_repl_heartbeat_not_suppressed_when_identity_user_custom(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir()
            (root / "IDENTITY.md").write_text("# 身份\n\n已约定称呼。\n", encoding="utf-8")
            (root / "USER.md").write_text("# 用户\n\n偏好已记录。\n", encoding="utf-8")
            _touch(root / "SOUL.md")
            _touch(root / "MEMORY.md")
            _touch(root / "transcript.jsonl")
            self.assertFalse(repl_heartbeat_suppressed_for_workspace_bootstrap(root))


if __name__ == "__main__":
    unittest.main()
