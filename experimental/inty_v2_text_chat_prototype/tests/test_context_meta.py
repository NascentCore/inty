"""load_context_meta: missing file defaults; invalid JSON fails with path context."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
if str(_EXPERIMENTAL) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.models import ContextMeta, load_context_meta


class TestLoadContextMeta(unittest.TestCase):
    def test_missing_file_returns_default(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "context.json"
            m = load_context_meta(p)
            self.assertEqual(m, ContextMeta())

    def test_invalid_json_raises_value_error_with_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "context.json"
            p.write_text("{not json", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                load_context_meta(p)
            self.assertIn("invalid JSON", str(ctx.exception))
            self.assertIn(str(p), str(ctx.exception))
            self.assertIsNotNone(ctx.exception.__cause__)


if __name__ == "__main__":
    unittest.main()
