"""ai_private.md 缓存与落盘。"""

from __future__ import annotations

import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.inty_v2_repl import ai_private_store
from tools.inty_v2_repl.paths import WorkspacePaths


class TestAiPrivateStore(unittest.TestCase):
    def test_load_missing_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            paths = WorkspacePaths(root=root)
            paths.ai_private_md.parent.mkdir(parents=True, exist_ok=True)
            self.assertEqual(ai_private_store.load_if_needed(root), "")

    def test_apply_then_load_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            paths = WorkspacePaths(root=root)
            paths.root.mkdir(parents=True, exist_ok=True)
            ai_private_store.apply_new_content(root, "line1\n")
            self.assertEqual(paths.ai_private_md.read_text(encoding="utf-8"), "line1\n")
            ai_private_store.invalidate_cache(root)
            self.assertEqual(ai_private_store.load_if_needed(root), "line1\n")

    def test_apply_exceeds_max_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            paths = WorkspacePaths(root=root)
            paths.root.mkdir(parents=True, exist_ok=True)
            with patch.dict(os.environ, {"INTY_V2_PROTO_AI_PRIVATE_MAX_CHARS": "10"}):
                with self.assertRaises(ValueError):
                    ai_private_store.apply_new_content(root, "x" * 20)

    def test_concurrent_apply_leaves_consistent_md(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            paths = WorkspacePaths(root=root)
            paths.root.mkdir(parents=True, exist_ok=True)
            barrier = threading.Barrier(2)
            errors: list[BaseException] = []

            def worker(text: str) -> None:
                try:
                    barrier.wait()
                    ai_private_store.apply_new_content(root, text)
                except BaseException as e:
                    errors.append(e)

            t1 = threading.Thread(target=worker, args=("aaa",))
            t2 = threading.Thread(target=worker, args=("bbb",))
            t1.start()
            t2.start()
            t1.join()
            t2.join()
            self.assertEqual(errors, [])
            got = paths.ai_private_md.read_text(encoding="utf-8")
            self.assertIn(got, ("aaa", "bbb"))
