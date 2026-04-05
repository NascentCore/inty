"""ensure_workspace_skeleton：只补缺、不覆盖已有文件。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.bootstrap import ensure_workspace_skeleton
from inty_v2_text_chat_prototype.memory_store_registry import shutdown_memory_store


class TestEnsureWorkspaceSkeleton(unittest.TestCase):
    def test_fills_missing_templates_without_overwriting_existing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir()
            custom = "KEEP_ME\n"
            (root / "IDENTITY.md").write_text(custom, encoding="utf-8")
            ensure_workspace_skeleton(root, write_context=False)
            self.assertEqual((root / "IDENTITY.md").read_text(encoding="utf-8"), custom)
            self.assertTrue((root / "SOUL.md").is_file())
            self.assertTrue((root / "USER.md").is_file())
            self.assertTrue((root / "MEMORY.md").is_file())
            self.assertFalse((root / "MODES.md").exists())
            self.assertFalse((root / "AGENTS.md").exists())
            self.assertTrue((root / "BOOSTRAP.md").is_file())
            self.assertTrue((root / "transcript.jsonl").is_file())
            shutdown_memory_store(root, timeout_s=2.0)


if __name__ == "__main__":
    unittest.main()
