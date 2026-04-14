"""workspace_init_tools.resolve_under_workspace 边界：禁止逃出 workspace。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.workspace_init_tools import resolve_under_workspace


class TestResolveUnderWorkspace(unittest.TestCase):
    def test_root_empty_string(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir()
            got = resolve_under_workspace(root, "")
            self.assertEqual(got, root.resolve())

    def test_nested_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir()
            (root / "a" / "b").mkdir(parents=True)
            p = root / "a" / "b" / "c.txt"
            p.write_text("x", encoding="utf-8")
            got = resolve_under_workspace(root, "a/b/c.txt")
            self.assertEqual(got, p.resolve())

    def test_rejects_absolute(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir()
            with self.assertRaises(ValueError):
                resolve_under_workspace(root, "/etc/passwd")

    def test_rejects_parent_escape(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir()
            with self.assertRaises(ValueError):
                resolve_under_workspace(root, "../outside.txt")


if __name__ == "__main__":
    unittest.main()
