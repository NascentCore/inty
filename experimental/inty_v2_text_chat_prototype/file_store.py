"""薄文件读写封装（无错误处理）。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_text_atomic(path: Path, content: str) -> None:
    """Write then rename into place so readers never see a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def append_line(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    need_leading_nl = False
    if path.is_file() and path.stat().st_size > 0:
        with path.open("rb") as rf:
            rf.seek(-1, os.SEEK_END)
            if rf.read(1) != b"\n":
                need_leading_nl = True
    with path.open("a", encoding="utf-8") as f:
        if need_leading_nl:
            f.write("\n")
        f.write(line)
        if not line.endswith("\n"):
            f.write("\n")


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    append_line(path, json.dumps(record, ensure_ascii=False))
