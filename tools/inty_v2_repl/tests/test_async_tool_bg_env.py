"""async_tool_background_enabled: default on, explicit opt-out, invalid raises."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.client import async_tool_background_enabled


class TestAsyncToolBgEnv(unittest.TestCase):
    def test_default_on_when_unset(self) -> None:
        with patch.dict(os.environ):
            os.environ.pop("INTY_V2_PROTO_ASYNC_TOOL_BG", None)
            self.assertTrue(async_tool_background_enabled())

    def test_explicit_off(self) -> None:
        for v in ("0", "false", "no", "off", "FALSE", "Off"):
            with patch.dict(
                os.environ, {"INTY_V2_PROTO_ASYNC_TOOL_BG": v}, clear=False
            ):
                self.assertFalse(async_tool_background_enabled(), v)

    def test_explicit_on(self) -> None:
        for v in ("1", "true", "yes", "on"):
            with patch.dict(
                os.environ, {"INTY_V2_PROTO_ASYNC_TOOL_BG": v}, clear=False
            ):
                self.assertTrue(async_tool_background_enabled(), v)

    def test_invalid_raises(self) -> None:
        with patch.dict(
            os.environ, {"INTY_V2_PROTO_ASYNC_TOOL_BG": "maybe"}, clear=False
        ):
            with self.assertRaises(ValueError) as ctx:
                async_tool_background_enabled()
        self.assertIn("INTY_V2_PROTO_ASYNC_TOOL_BG", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
