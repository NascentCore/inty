"""load_prototype_dotenv: loads cwd .env via a single load_dotenv() call."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.client import load_prototype_dotenv


def test_load_prototype_dotenv_calls_load_dotenv_once() -> None:
    with patch("inty_v2_text_chat_prototype.client.load_dotenv") as mock_ld:
        load_prototype_dotenv()
    assert mock_ld.call_count == 1
    mock_ld.assert_called_once_with()
