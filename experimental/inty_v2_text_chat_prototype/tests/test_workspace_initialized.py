"""is_workspace_initialized：与 run_turn 所需五件套一致。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.orchestrator import is_workspace_initialized


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


if __name__ == "__main__":
    unittest.main()
