"""fal_client 全局 async client 与短生命周期 asyncio.run 的兼容性。"""

from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

import fal_client
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from experimental.inty_v2_text_chat_prototype.fal_z_image_tool import (
    _reset_fal_async_client_after_short_lived_loop,
)


class TestFalAsyncClientReset(unittest.TestCase):
    def test_two_asyncio_runs_after_reset_recreate_client(self) -> None:
        """复现 REPL 多次 generate_image：每轮 asyncio.run 后须拆掉绑定到已关闭 loop 的缓存。"""

        async def iteration() -> None:
            _ = fal_client.async_client._client
            self.assertIn("_client", fal_client.async_client.__dict__)
            await _reset_fal_async_client_after_short_lived_loop()
            self.assertNotIn("_client", fal_client.async_client.__dict__)
            self.assertNotIn("_token_manager", fal_client.async_client.__dict__)

        with patch(
            "fal_client.client.fetch_credentials",
            return_value="dummy-test-key",
        ):
            asyncio.run(iteration())
            asyncio.run(iteration())


if __name__ == "__main__":
    unittest.main()
