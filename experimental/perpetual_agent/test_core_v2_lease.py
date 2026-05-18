from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from experimental.perpetual_agent.core_v2.repositories.lease_repo import (
    LeaseRepository,
)
from experimental.perpetual_agent.core_v2.repositories.sqlite_db import (
    SQLiteDatabase,
)
from experimental.perpetual_agent.core_v2.repositories.sqlite_schema import (
    init_schema,
)


def _db(tmp_path: Path) -> SQLiteDatabase:
    db = SQLiteDatabase(str(tmp_path / "core_v2.sqlite3"))
    init_schema(db)
    return db


def test_single_consumer_lease_exclusive_until_expired(tmp_path: Path) -> None:
    db = _db(tmp_path)
    repo = LeaseRepository(db)
    now = datetime(2026, 3, 24, tzinfo=timezone.utc)
    assert repo.try_acquire_or_renew(
        lease_key="telegram_inbound",
        owner_id="owner_a",
        ttl_seconds=30,
        now=now,
    )
    assert not repo.try_acquire_or_renew(
        lease_key="telegram_inbound",
        owner_id="owner_b",
        ttl_seconds=30,
        now=now + timedelta(seconds=10),
    )
    assert repo.try_acquire_or_renew(
        lease_key="telegram_inbound",
        owner_id="owner_b",
        ttl_seconds=30,
        now=now + timedelta(seconds=31),
    )


def test_release_only_by_owner(tmp_path: Path) -> None:
    db = _db(tmp_path)
    repo = LeaseRepository(db)
    now = datetime(2026, 3, 24, tzinfo=timezone.utc)
    repo.try_acquire_or_renew(
        lease_key="telegram_inbound",
        owner_id="owner_a",
        ttl_seconds=30,
        now=now,
    )
    assert not repo.release_if_owner(
        lease_key="telegram_inbound",
        owner_id="owner_b",
    )
    assert repo.release_if_owner(
        lease_key="telegram_inbound",
        owner_id="owner_a",
    )
