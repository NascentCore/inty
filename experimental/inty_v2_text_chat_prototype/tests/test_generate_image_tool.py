"""generate_image 工具：参数校验与 Fal 调用桩。"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_EXPERIMENTAL))
sys.path.insert(0, str(_REPO_ROOT))

from inty_v2_text_chat_prototype.fal_z_image_tool import MAX_NUM_IMAGES_PER_CALL
from inty_v2_text_chat_prototype.image_gate import prepare_image_gate_for_turn
from inty_v2_text_chat_prototype.workspace_init_tools import execute_tool_call_blocking


async def _fake_z_image_turbo_call(
    _args: object, _gcs_uri_base: str, **_kwargs: object
) -> list[SimpleNamespace]:
    return [
        SimpleNamespace(
            gcs_http_url="https://example.com/fake.jpg",
            size=SimpleNamespace(width=640, height=480),
            raw_data=b"\xff\xd8\xff\xd9",
            format=SimpleNamespace(value="jpeg"),
        )
    ]


async def _fake_z_image_turbo_call_two(
    _args: object, _gcs_uri_base: str, **_kwargs: object
) -> list[SimpleNamespace]:
    return [
        SimpleNamespace(
            gcs_http_url="https://example.com/a.jpg",
            size=SimpleNamespace(width=1, height=1),
            raw_data=b"\xaa",
            format=SimpleNamespace(value="jpeg"),
        ),
        SimpleNamespace(
            gcs_http_url="https://example.com/b.jpg",
            size=SimpleNamespace(width=2, height=2),
            raw_data=b"\xbb",
            format=SimpleNamespace(value="jpeg"),
        ),
    ]


class TestGenerateImageTool(unittest.TestCase):
    def _init_workspace(self, root: Path) -> None:
        (root / "IDENTITY.md").write_text("# I\n", encoding="utf-8")
        (root / "SOUL.md").write_text("# S\n", encoding="utf-8")
        (root / "USER.md").write_text("# U\n", encoding="utf-8")
        (root / "MEMORY.md").write_text("# M\n", encoding="utf-8")
        (root / "transcript.jsonl").write_text("", encoding="utf-8")
        prepare_image_gate_for_turn(root, "生成图片")

    def test_empty_prompt_errors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_workspace(root)
            out = execute_tool_call_blocking(
                root,
                "generate_image",
                json.dumps({"prompt": ""}),
            )
            self.assertTrue(out.startswith("ERROR:"))

    def test_num_images_zero_errors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_workspace(root)
            out = execute_tool_call_blocking(
                root,
                "generate_image",
                json.dumps({"prompt": "a cat", "num_images": 0}),
            )
            self.assertIn("num_images", out)
            self.assertTrue(out.startswith("ERROR:"))

    def test_num_images_above_cap_errors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_workspace(root)
            out = execute_tool_call_blocking(
                root,
                "generate_image",
                json.dumps({"prompt": "x", "num_images": MAX_NUM_IMAGES_PER_CALL + 1}),
            )
            self.assertTrue(out.startswith("ERROR:"))
            self.assertIn(str(MAX_NUM_IMAGES_PER_CALL), out)

    def test_success_writes_local_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_workspace(root)
            with patch(
                "inty_v2_text_chat_prototype.fal_z_image_tool._z_image_turbo_call",
                new=_fake_z_image_turbo_call,
            ):
                out = execute_tool_call_blocking(
                    root,
                    "generate_image",
                    json.dumps({"prompt": "test scene"}),
                )
            self.assertIn("generate_image: OK", out)
            self.assertIn("requested=1", out)
            self.assertIn("returned=1", out)
            self.assertIn("gcs_http_url=https://example.com/fake.jpg", out)
            self.assertIn("size=640x480", out)
            self.assertIn("local_path=", out)
            self.assertIn("asset_id=", out)
            self.assertIn("persona_revision_id=", out)
            gen_dir = root / "generated_images"
            self.assertTrue(gen_dir.is_dir())
            files = list(gen_dir.glob("z_image_*.jpeg"))
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].read_bytes(), b"\xff\xd8\xff\xd9")
            idx = root / "generated_images" / "index.jsonl"
            self.assertTrue(idx.is_file())

    def test_multi_image_summary_numbered(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_workspace(root)
            with patch(
                "inty_v2_text_chat_prototype.fal_z_image_tool._z_image_turbo_call",
                new=_fake_z_image_turbo_call_two,
            ):
                out = execute_tool_call_blocking(
                    root,
                    "generate_image",
                    json.dumps({"prompt": "two moods", "num_images": 2}),
                )
            self.assertIn("requested=2", out)
            self.assertIn("returned=2", out)
            self.assertIn("#1:", out)
            self.assertIn("#2:", out)
            self.assertIn("gcs_http_url=https://example.com/a.jpg", out)
            self.assertIn("gcs_http_url=https://example.com/b.jpg", out)
            self.assertIn("asset_id=", out)


if __name__ == "__main__":
    unittest.main()
