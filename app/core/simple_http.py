"""Thin HTTP helpers for app code paths that must not scatter raw clients."""

from __future__ import annotations

from typing import Any

import requests


def http_get_json(
    url: str,
    *,
    params: dict[str, str | int | None],
    timeout_sec: float = 30.0,
) -> dict[str, Any]:
    clean = {k: v for k, v in params.items() if v is not None}
    r = requests.get(url, params=clean, timeout=timeout_sec)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object from {url!r}, got {type(data).__name__}")
    return data
