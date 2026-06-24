"""Postgres advisory lock for one companion scope dreaming batch.

Generated entirely by Cursor agent for HYGIENE-2026-12 (#3550).

When MemoryStore is repository-backed, ``try_dreaming_scope_advisory_lock`` uses
``pg_try_advisory_lock`` keyed by scope registry key so multi-process Ops cannot
run two dreaming batches for the same scope concurrently. In-memory stores skip
the lock (single-process prototype).
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from contextlib import contextmanager


def _dreaming_advisory_lock_key(scope_registry_key: str) -> int:
    digest = hashlib.sha256(
        f"dreaming:{scope_registry_key}".encode()
    ).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=True)


@contextmanager
def try_dreaming_scope_advisory_lock(
    scope_registry_key: str,
) -> Iterator[bool]:
    """Yield whether this process holds the scope dreaming advisory lock."""
    assert scope_registry_key != ""
    from sqlalchemy import text

    from app.db.base import SessionLocal

    key = _dreaming_advisory_lock_key(scope_registry_key)
    session = SessionLocal()
    acquired = False
    try:
        acquired = bool(
            session.execute(
                text("SELECT pg_try_advisory_lock(:lock_key)"),
                {"lock_key": key},
            ).scalar()
        )
        yield acquired
    finally:
        if acquired:
            session.execute(
                text("SELECT pg_advisory_unlock(:lock_key)"),
                {"lock_key": key},
            )
        session.close()
