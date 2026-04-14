"""Google Custom Search JSON API — REPL tool backend."""

from __future__ import annotations

import os
from typing import Any

import httpx

_CSE_URL = "https://www.googleapis.com/customsearch/v1"
_MAX_NUM = 10


def _env_api_key() -> str | None:
    v = os.environ.get("GOOGLE_CSE_API_KEY")
    return v.strip() if isinstance(v, str) and v.strip() else None


def _env_cx() -> str | None:
    v = os.environ.get("GOOGLE_CSE_ID")
    return v.strip() if isinstance(v, str) and v.strip() else None


def _format_items(items: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for i, it in enumerate(items, start=1):
        title = str(it.get("title", "")).strip()
        link = str(it.get("link", "")).strip()
        snip = str(it.get("snippet", "")).strip()
        block = f"{i}. {title}\n   URL: {link}"
        if snip:
            block += f"\n   {snip}"
        lines.append(block)
    return "\n\n".join(lines)


async def run_google_web_search(*, query: str, num_results: int | None) -> str:
    """
    Call Google Programmable Search (Custom Search JSON API).
    Requires GOOGLE_CSE_API_KEY and GOOGLE_CSE_ID in the environment.
    """
    q = query.strip()
    if not q:
        return "ERROR: query must be non-empty"

    key = _env_api_key()
    cx = _env_cx()
    if not key or not cx:
        return (
            "ERROR: set GOOGLE_CSE_API_KEY and GOOGLE_CSE_ID "
            "(Google Cloud Custom Search API + Programmable Search Engine cx)"
        )

    n = num_results if num_results is not None else 10
    if n < 1:
        return "ERROR: num_results must be at least 1"
    n = min(n, _MAX_NUM)

    params = {"key": key, "cx": cx, "q": q, "num": str(n)}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(_CSE_URL, params=params)
    except httpx.TimeoutException as exc:
        return f"ERROR: Google CSE request timed out: {exc}"
    except httpx.RequestError as exc:
        return f"ERROR: Google CSE request failed: {exc}"

    if resp.status_code != 200:
        return f"ERROR: Google CSE HTTP {resp.status_code}: {resp.text[:500]}"

    try:
        data = resp.json()
    except ValueError as exc:
        return f"ERROR: invalid JSON from Google CSE: {exc}"

    items = data.get("items")
    if not isinstance(items, list) or len(items) == 0:
        return "(no results)"

    normalized: list[dict[str, Any]] = []
    for raw in items:
        if isinstance(raw, dict):
            normalized.append(raw)
    if not normalized:
        return "(no results)"

    return _format_items(normalized)
