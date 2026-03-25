"""load_context_meta: missing file defaults; invalid JSON fails with path context."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.models import ContextMeta, load_context_meta


def test_missing_file_returns_default(tmp_path: Path) -> None:
    p = tmp_path / "context.json"
    m = load_context_meta(p)
    assert m == ContextMeta()


def test_invalid_json_raises_value_error_with_path(tmp_path: Path) -> None:
    p = tmp_path / "context.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON") as ei:
        load_context_meta(p)
    assert str(p) in str(ei.value)
    assert ei.value.__cause__ is not None
