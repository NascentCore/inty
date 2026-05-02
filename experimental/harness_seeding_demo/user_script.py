"""Load fixed user lines from JSON or plain text (one non-empty line per turn)."""

from __future__ import annotations

import json
from pathlib import Path


def load_user_script(path: Path) -> list[str]:
    p = path.resolve()
    raw = p.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    if p.suffix.lower() == ".json":
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip()]
        if isinstance(data, dict) and "lines" in data:
            return [str(x).strip() for x in data["lines"] if str(x).strip()]
        raise ValueError("JSON script must be a list of strings or {\"lines\": [...]}")
    out: list[str] = []
    for line in raw.splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            out.append(s)
    return out
