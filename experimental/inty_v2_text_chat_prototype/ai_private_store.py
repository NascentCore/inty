"""Workspace ai_private.md：进程内缓存、原子落盘、JSONL/DB 镜像（与 transcript 同 append_jsonl_with_db）。"""

from __future__ import annotations

import os
import threading
from pathlib import Path

from .file_store import read_text, write_text_atomic
from .jsonl_db_store import append_jsonl_with_db
from .models import AI_PRIVATE_INJECT_MAX_CHARS
from .paths import WorkspacePaths
from .utc import utc_iso_ts

_LOCK = threading.Lock()
_STATE: dict[str, dict[str, object]] = {}


def _default_max_chars() -> int:
    raw = os.environ.get("INTY_V2_PROTO_AI_PRIVATE_MAX_CHARS")
    if raw is None or not str(raw).strip():
        return AI_PRIVATE_INJECT_MAX_CHARS
    return int(str(raw).strip())


def _state_key(root: Path) -> str:
    return str(root.resolve())


def load_if_needed(root: Path) -> str:
    """首次访问时从磁盘读入缓存；文件不存在则缓存空串。"""
    key = _state_key(root)
    with _LOCK:
        st = _STATE.get(key)
        if st is None:
            st = {"text": "", "loaded": False}
            _STATE[key] = st
        if st["loaded"] is True:
            return str(st["text"])
        paths = WorkspacePaths(root=Path(key))
        if paths.ai_private_md.is_file():
            st["text"] = read_text(paths.ai_private_md)
        else:
            st["text"] = ""
        st["loaded"] = True
        return str(st["text"])


def get_text_for_prompt(root: Path, *, max_chars: int | None = None) -> str:
    cap = max_chars if max_chars is not None else _default_max_chars()
    s = load_if_needed(root)
    if len(s) <= cap:
        return s
    return s[: cap - 1] + "…"


def apply_new_content(root: Path, text: str) -> None:
    """更新缓存、原子写 md、追加 ai_private.jsonl（及 PG 流）。"""
    max_c = _default_max_chars()
    if len(text) > max_c:
        raise ValueError(
            f"ai_private content len={len(text)} exceeds INTY_V2_PROTO_AI_PRIVATE_MAX_CHARS={max_c}"
        )
    key = _state_key(root)
    paths = WorkspacePaths(root=Path(key))
    with _LOCK:
        write_text_atomic(paths.ai_private_md, text)
        append_jsonl_with_db(
            paths.ai_private_jsonl,
            {
                "ts": utc_iso_ts(),
                "byte_len": len(text.encode("utf-8")),
                "content": text,
            },
        )
        st = _STATE.setdefault(key, {"text": "", "loaded": False})
        st["text"] = text
        st["loaded"] = True


def invalidate_cache(root: Path) -> None:
    """测试或外部改写文件后丢弃缓存。"""
    key = _state_key(root)
    with _LOCK:
        if key in _STATE:
            _STATE[key]["loaded"] = False
