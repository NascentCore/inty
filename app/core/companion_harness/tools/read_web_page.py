"""Download a web page, extract readable text, summarize as markdown bullets, append to MEMORY.md.

TODO(#3674): When Browserbase is enabled, render via remote browser as picture
(this allows more human-like perception instead of reading like machine code)
before summarizing — epic #3672.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from app.core.companion_harness.companion.utc import utc_iso_ts
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)

_MAX_HTML_BYTES = 2_000_000
_DEFAULT_BULLETS = 10
_MIN_BULLETS = 3
_MAX_BULLETS_CAP = 20
_USER_AGENT = "Mozilla/5.0 (compatible; IntyCompanionReadWeb/1.0)"


def _validate_public_http_url(url: str) -> str | None:
    raw = url.strip()
    if not raw:
        return "URL must be non-empty"
    try:
        parsed = urlparse(raw)
    except ValueError:
        return "invalid URL"
    if parsed.scheme not in ("http", "https"):
        return "only http and https URLs are allowed"
    host = (parsed.hostname or "").lower()
    if not host:
        return "URL must include a hostname"
    if host in ("localhost", "127.0.0.1", "::1") or host.endswith(".localhost"):
        return "local URLs are not allowed"
    return None


def _pick_main_root(soup: BeautifulSoup) -> Any:
    for sel in ("article", "main", '[role="main"]'):
        node = soup.select_one(sel)
        if node is not None:
            return node
    return soup.body if soup.body else soup


def _html_to_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    title_el = soup.find("title")
    title = (title_el.get_text(strip=True) if title_el else "") or ""
    og = soup.find("meta", property="og:title")
    if og is not None:
        content = og.get("content")
        if isinstance(content, str) and content.strip():
            title = content.strip()
    root = _pick_main_root(soup)
    for tag in root.find_all(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = root.get_text("\n")
    lines: list[str] = []
    for line in text.splitlines():
        s = " ".join(line.split())
        if s:
            lines.append(s)
    body = "\n".join(lines)
    return title.strip(), body


_SENT_SPLIT = re.compile(r"(?<=[.!?。！？])\s+")


def _paragraphs_and_sentences(body: str, max_bullets: int) -> list[str]:
    if not body.strip():
        return []
    chunks: list[str] = []
    paras = [p.strip() for p in re.split(r"\n\s*\n+", body) if p.strip()]
    for p in paras:
        if len(chunks) >= max_bullets * 3:
            break
        if len(p) <= 500:
            chunks.append(p)
        else:
            parts = [s.strip() for s in _SENT_SPLIT.split(p) if s.strip()]
            for s in parts:
                if len(chunks) >= max_bullets * 3:
                    break
                if len(s) > 15:
                    chunks.append(s)
    seen: set[str] = set()
    out: list[str] = []
    for c in chunks:
        key = c[:240]
        if key in seen:
            continue
        seen.add(key)
        if len(c) < 20:
            continue
        out.append(c)
        if len(out) >= max_bullets:
            break
    return out


def _build_summary_markdown(
    title: str, bullets: list[str], url: str, *, memory_note: str
) -> str:
    lines: list[str] = []
    head = title if title else url
    lines.append(f"# {head}")
    lines.append("")
    for b in bullets:
        lines.append(f"- {b}")
    lines.append("")
    lines.append(f"Source: {url}")
    lines.append(f"Fetched (UTC): {utc_iso_ts()}")
    lines.append("")
    lines.append(memory_note)
    return "\n".join(lines)


def _append_memory_block(
    store: MemoryStore,
    *,
    url: str,
    title: str,
    bullets: list[str],
) -> None:
    memory_rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.memory_md
    prev = store.read_document_if_exists(memory_rel) or ""
    ts = utc_iso_ts()
    block_lines = [
        f"### Web snapshot · read_web_page · {ts}",
        f"- **URL**: {url}",
    ]
    if title:
        block_lines.append(f"- **Title**: {title}")
    block_lines.append("- **Takeaways**:")
    for b in bullets:
        block_lines.append(f"  - {b}")
    block = "\n".join(block_lines)
    merged = prev.rstrip() + "\n\n" + block + "\n"
    store.write_document(memory_rel, merged)


def run_read_web_page_sync(
    store: MemoryStore,
    *,
    url: str,
    max_bullets: int | None = None,
) -> str:
    err = _validate_public_http_url(url)
    if err:
        return f"ERROR: {err}"

    n = max_bullets if max_bullets is not None else _DEFAULT_BULLETS
    n = max(_MIN_BULLETS, min(n, _MAX_BULLETS_CAP))

    try:
        r = requests.get(
            url.strip(),
            timeout=30.0,
            headers={"User-Agent": _USER_AGENT},
            allow_redirects=True,
        )
        r.raise_for_status()
    except requests.RequestException as exc:
        return f"ERROR: failed to fetch URL: {exc}"

    raw = r.content
    if len(raw) > _MAX_HTML_BYTES:
        return (
            f"ERROR: response body too large ({len(raw)} bytes); "
            f"max {_MAX_HTML_BYTES} bytes"
        )

    ctype = (r.headers.get("Content-Type") or "").lower()
    looks_html = "html" in ctype or url.lower().rstrip("/").endswith(
        (".html", ".htm")
    )
    if not looks_html:
        sample = raw[:500].decode("utf-8", errors="replace").lower()
        if "<html" not in sample and "<!doctype" not in sample:
            return "ERROR: response does not look like HTML"

    enc = r.encoding or "utf-8"
    try:
        html = raw.decode(enc, errors="replace")
    except LookupError:
        html = raw.decode("utf-8", errors="replace")

    title, body = _html_to_text(html)
    bullets = _paragraphs_and_sentences(body, n)
    if not bullets:
        bullets = [
            "(Could not extract enough body text; the page may be script-rendered or empty.)"
        ]

    try:
        _append_memory_block(
            store, url=url.strip(), title=title, bullets=bullets
        )
    except OSError as exc:
        return f"ERROR: could not write MEMORY.md: {exc}"

    memory_rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.memory_md
    memory_note = f"Memory: appended this snapshot to `{memory_rel}`."
    return _build_summary_markdown(
        title, bullets, url.strip(), memory_note=memory_note
    )


async def run_read_web_page(
    store: MemoryStore,
    *,
    url: str,
    max_bullets: int | None = None,
) -> str:
    return await asyncio.to_thread(
        run_read_web_page_sync, store, url=url, max_bullets=max_bullets
    )
