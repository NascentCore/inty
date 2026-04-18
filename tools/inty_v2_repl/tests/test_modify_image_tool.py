"""modify_image 工具：与 generate_image 区分，走 Fal image-to-image。"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
if str(_EXPERIMENTAL) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENTAL))

from app.core.agentic_kernel.companion.image_gate import list_image_asset_records
from app.core.images.types import GeneratedImageProcessResult
from app.utils.image import ImageFormat, ImageSize
from inty_v2_repl.memory_store_registry import get_memory_store
from inty_v2_repl.workspace_init_tools import execute_tool_call_blocking


async def _fake_z_image_turbo_image_to_image(
    _args: object, _gcs_uri_base: str, **_kwargs: object
) -> GeneratedImageProcessResult:
    return GeneratedImageProcessResult(
        size=ImageSize(width=64, height=64),
        format=ImageFormat.PNG,
        raw_data=b"\x89PNG\r\n",
        raw_data_total_bytes=6,
        gcs_uri="gs://test-bucket/obj",
        gcs_http_url="https://example.com/edited.png",
        generated_at=datetime.now(timezone.utc),
        raw_response_from_provider=None,
    )


class TestModifyImageTool(unittest.TestCase):
    def test_no_source_errors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = execute_tool_call_blocking(
                root,
                "modify_image",
                json.dumps({"prompt": "make it warmer"}),
            )
            self.assertTrue(out.startswith("ERROR:"))

    def test_no_source_uses_latest_generated_image(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            st = get_memory_store(root)
            st.append_jsonl_record(
                "generated_images/index.jsonl",
                {
                    "asset_id": "a-old",
                    "gcs_http_url": "https://example.com/old-from-index.png",
                    "local_path_relative": "generated_images/old.jpg",
                },
            )
            st.append_jsonl_record(
                "generated_images/index.jsonl",
                {
                    "asset_id": "a-new",
                    "gcs_http_url": "https://example.com/uploaded-latest.png",
                    "local_path_relative": "generated_images/new.png",
                },
            )
            with patch(
                "app.core.agentic_kernel.companion.fal_z_image_tool._z_image_turbo_i2i_call",
                new=_fake_z_image_turbo_image_to_image,
            ):
                out = execute_tool_call_blocking(
                    root,
                    "modify_image",
                    json.dumps(
                        {
                            "prompt": "make it cooler",
                        }
                    ),
                )
            self.assertIn("modify_image: OK", out)
            self.assertIn("https://example.com/edited.png", out)

    def test_both_sources_errors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "a.jpg"
            p.write_bytes(b"\xff\xd8\xff\xd9")
            out = execute_tool_call_blocking(
                root,
                "modify_image",
                json.dumps(
                    {
                        "prompt": "x",
                        "source_image_relative_path": "a.jpg",
                        "source_image_url": "https://example.com/x.jpg",
                    }
                ),
            )
            self.assertTrue(out.startswith("ERROR:"))
            self.assertIn("only one", out.lower())

    def test_strength_out_of_range(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = execute_tool_call_blocking(
                root,
                "modify_image",
                json.dumps(
                    {
                        "prompt": "x",
                        "source_image_url": "https://example.com/x.jpg",
                        "strength": 1.5,
                    }
                ),
            )
            self.assertTrue(out.startswith("ERROR:"))
            self.assertIn("strength", out)

    def test_success_with_url(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch(
                "app.core.agentic_kernel.companion.fal_z_image_tool._z_image_turbo_i2i_call",
                new=_fake_z_image_turbo_image_to_image,
            ):
                out = execute_tool_call_blocking(
                    root,
                    "modify_image",
                    json.dumps(
                        {
                            "prompt": "add soft light",
                            "source_image_url": "https://example.com/in.jpg",
                        }
                    ),
                )
            self.assertIn("modify_image: OK", out)
            self.assertIn("image-to-image", out)
            self.assertIn("gcs_http_url=https://example.com/edited.png", out)

    def test_success_with_workspace_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "IDENTITY.md").write_text("# I\n", encoding="utf-8")
            (root / "SOUL.md").write_text("# S\n", encoding="utf-8")
            (root / "USER.md").write_text("# U\n", encoding="utf-8")
            rel = "generated_images/src.jpeg"
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"\xff\xd8\xff\xd9")
            src_asset_id = "src-asset-1"
            src_revision = "rev-source-1"
            get_memory_store(root).append_jsonl_record(
                "generated_images/index.jsonl",
                {
                    "asset_id": src_asset_id,
                    "tool_name": "generate_image",
                    "persona_revision_id": src_revision,
                    "local_path_relative": rel,
                    "gcs_http_url": "https://example.com/src.jpg",
                },
            )
            with patch(
                "app.core.agentic_kernel.companion.fal_z_image_tool._z_image_turbo_i2i_call",
                new=_fake_z_image_turbo_image_to_image,
            ):
                out = execute_tool_call_blocking(
                    root,
                    "modify_image",
                    json.dumps(
                        {
                            "prompt": "cooler tones",
                            "source_image_relative_path": rel,
                        }
                    ),
                )
            self.assertIn("modify_image: OK", out)
            self.assertIn("asset_id=", out)
            self.assertIn("persona_revision_id=", out)
            rows = list_image_asset_records(root)
            self.assertGreaterEqual(len(rows), 2)
            last = rows[-1]
            self.assertEqual(last.get("tool_name"), "modify_image")
            self.assertEqual(last.get("image_mode"), "modify")


if __name__ == "__main__":
    unittest.main()
