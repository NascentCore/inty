"""P0 image-gate: profile persist ordering + mode confirmation."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
if str(_EXPERIMENTAL) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.image_gate import (
    check_image_tool_allowed,
    current_persona_revision_id,
    prepare_image_gate_for_turn,
    register_profile_write,
)


class TestImageGateP0(unittest.TestCase):
    def _init_workspace(self, root: Path) -> None:
        (root / "IDENTITY.md").write_text("# I\n\n性别：女\n", encoding="utf-8")
        (root / "SOUL.md").write_text("# S\n", encoding="utf-8")
        (root / "USER.md").write_text("# U\n", encoding="utf-8")
        (root / "MEMORY.md").write_text("# M\n", encoding="utf-8")
        (root / "transcript.jsonl").write_text("", encoding="utf-8")

    def test_requires_profile_persist_before_image_when_same_turn_mentions_both(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_workspace(root)
            prepare_image_gate_for_turn(root, "把性别改成男，然后生成图片")
            err = check_image_tool_allowed(root, tool_name="generate_image")
            self.assertIsNotNone(err)
            assert err is not None
            self.assertIn("persist profile docs", err)

            ident = (root / "IDENTITY.md").read_text(encoding="utf-8")
            (root / "IDENTITY.md").write_text(
                ident.replace("女", "男"), encoding="utf-8"
            )
            register_profile_write(root, "IDENTITY.md", changed=True)

            # Persist gate is cleared after profile write; then mode confirmation blocks image tool.
            err2 = check_image_tool_allowed(root, tool_name="generate_image")
            self.assertIsNotNone(err2)
            assert err2 is not None
            self.assertIn("choose image mode first", err2)

    def test_mode_confirmation_regenerate_vs_modify(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_workspace(root)
            before = current_persona_revision_id(root)

            prepare_image_gate_for_turn(root, "把性别改成男")
            ident = (root / "IDENTITY.md").read_text(encoding="utf-8")
            (root / "IDENTITY.md").write_text(
                ident.replace("性别：女", "性别：男"), encoding="utf-8"
            )
            register_profile_write(root, "IDENTITY.md", changed=True)
            after = current_persona_revision_id(root)
            self.assertNotEqual(before, after)

            # No mode yet -> blocked
            err = check_image_tool_allowed(root, tool_name="generate_image")
            self.assertIsNotNone(err)
            assert err is not None
            self.assertIn("choose image mode first", err)

            # choose modify
            prepare_image_gate_for_turn(root, "基于旧图改图")
            self.assertIsNone(check_image_tool_allowed(root, tool_name="modify_image"))
            err2 = check_image_tool_allowed(root, tool_name="generate_image")
            self.assertIsNotNone(err2)
            assert err2 is not None
            self.assertIn("selected modify-existing", err2)

            # choose regenerate
            prepare_image_gate_for_turn(root, "按新设定重生图")
            self.assertIsNone(check_image_tool_allowed(root, tool_name="generate_image"))
            err3 = check_image_tool_allowed(root, tool_name="modify_image")
            self.assertIsNotNone(err3)
            assert err3 is not None
            self.assertIn("selected regenerate-from-scratch", err3)

    def test_only_real_profile_change_creates_pending_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_workspace(root)
            prepare_image_gate_for_turn(root, "修改设定")
            register_profile_write(root, "IDENTITY.md", changed=False)
            self.assertIsNone(check_image_tool_allowed(root, tool_name="generate_image"))

            # Ensure state file remains valid JSON
            state_path = root / ".inty_v2_image_gate.json"
            self.assertTrue(state_path.is_file())
            raw = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertIsInstance(raw, dict)


if __name__ == "__main__":
    unittest.main()
