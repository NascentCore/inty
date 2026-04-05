"""load_prototype_dotenv: loads cwd .env then package .env for unset keys."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import call, patch

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.client import load_prototype_dotenv


def test_load_prototype_dotenv_calls_load_dotenv_cwd_then_package() -> None:
    pkg_env = Path(__file__).resolve().parent.parent / ".env"
    with patch("inty_v2_text_chat_prototype.client.load_dotenv") as mock_ld:
        load_prototype_dotenv()
    assert mock_ld.call_count == 2
    mock_ld.assert_has_calls([call(), call(pkg_env)])
