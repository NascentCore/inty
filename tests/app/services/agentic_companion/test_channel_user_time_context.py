"""Tests for agent-channel ``UserTimeContext`` from USER.md."""

from __future__ import annotations

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.services.agentic_companion.channel_user_time_context import (
    build_user_time_context_for_iana,
    client_time_from_memory_store,
)


def test_build_user_time_context_for_iana_populates_fields() -> None:
    ctx = build_user_time_context_for_iana("Asia/Shanghai")
    assert ctx.timezone == "Asia/Shanghai"
    assert ctx.local_time is not None
    assert ctx.utc_offset_minutes == 480


def test_client_time_from_memory_store_reads_user_md_timezone(tmp_path) -> None:
    store = MemoryStore(
        scope=CompanionScope("u", "a", str(tmp_path.resolve())),
        repository=None,
    )
    store.write_document(
        "USER.md",
        "## 身份信息\n\n- 时区：Asia/Tokyo\n",
    )

    ctx = client_time_from_memory_store(store)

    assert ctx is not None
    assert ctx.timezone == "Asia/Tokyo"
