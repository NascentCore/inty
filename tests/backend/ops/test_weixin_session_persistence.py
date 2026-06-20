"""Tests for Weixin bridge Postgres persistence (sync DTO checks).

Async upsert/list/delete + restore scenarios: ``tests/backend/ops/test_weixin_session_restore.py``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.ops.weixin_session.session_persistence import (
    record_from_binding_fields,
)


def test_record_from_binding_fields_includes_weixin_creds() -> None:
    record = record_from_binding_fields(
        session_id="sess-d",
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="jwt-demo",
        agent_id="agent-weixin-static",
        weixin_account_id="wx-acct-1",
        weixin_token="tok-demo",
        weixin_base_url="https://ilink.example",
        last_peer_id="peer-9",
        last_peer_seen_at=datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc),
    )
    assert record.weixin_token == "tok-demo"
    assert record.weixin_base_url == "https://ilink.example"
