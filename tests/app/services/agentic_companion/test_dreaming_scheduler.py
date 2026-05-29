from __future__ import annotations

import asyncio

from app.services.agentic_companion.dreaming_scheduler import (
    DreamingScope,
    _advisory_unlock,
    _try_advisory_lock,
)


class _ScalarResult:
    def __init__(self, value: bool) -> None:
        self._value = value

    def scalar(self) -> bool:
        return self._value


class _FakeDb:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str]]] = []

    async def execute(self, stmt: object, params: dict[str, str]) -> _ScalarResult:
        self.calls.append((str(stmt), params))
        return _ScalarResult(True)


def test_dreaming_scope_lock_key() -> None:
    scope = DreamingScope(user_id="u", companion_id="a", chat_id="c")
    assert scope.lock_key == "companion-dreaming:u:a:c"


def test_dreaming_scheduler_advisory_lock_sql() -> None:
    db = _FakeDb()
    assert asyncio.run(_try_advisory_lock(db, "k")) is True
    asyncio.run(_advisory_unlock(db, "k"))
    sql_lines = [call[0] for call in db.calls]
    assert "pg_try_advisory_lock" in sql_lines[0]
    assert "hashtextextended" in sql_lines[0]
    assert "pg_advisory_unlock" in sql_lines[1]
    assert db.calls[0][1] == {"lock_key": "k"}
