"""bootstrap 完成但助手正文为空时，须注入 BOOSTRAP.md 要求的庆祝句。"""

from __future__ import annotations

import sys
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.orchestrator import (
    default_bootstrap_completion_celebration_text,
)


def test_default_bootstrap_completion_celebration_text() -> None:
    s = default_bootstrap_completion_celebration_text()
    assert s.strip()
    assert "🎉" in s
