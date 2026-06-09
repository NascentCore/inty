from __future__ import annotations

import json
import uuid

import pytest

from app.core.companion_harness.runtime.llm_client import CompanionLLMConfig
from app.core.companion_harness.runtime.manager import CompanionConfig, CompanionManager
from app.core.companion_harness.memory.memory_registry import shutdown_all_memory_stores
from app.core.companion_harness.tools.companion_tool_runtime import execute_tool_call
from app.techno_core.models import (
    TECHNO_CORE_EVENTS_JSONL_RELATIVE_PATH,
    TECHNO_CORE_RECORD_EVENT_TOOL_NAME,
)
from tests.app.core.companion_harness.companion_memory_registry_dsn import (
    companion_memory_registry_dsn,
)


@pytest.mark.asyncio
async def test_techno_core_record_event_appends_valid_jsonl() -> None:
    rid = uuid.uuid4().hex[:12]
    uid, cid, chid = f"u-tce-{rid}", f"c-tce-{rid}", f"chat-tce-{rid}"
    manager = CompanionManager(
        CompanionConfig(
            llm=CompanionLLMConfig(api_key="k"),
            memory_pg_dsn=companion_memory_registry_dsn(),
        )
    )
    session = manager.get_or_create_session(uid, cid, chid)
    store = session.store
    payload = {
        "sphere": "living_sphere",
        "summary": "在窗边把杯口的热气吹散了一点。",
        "visibility": "private",
        "related_living_sphere": "玻璃海岸小屋",
    }
    out = await execute_tool_call(
        store,
        TECHNO_CORE_RECORD_EVENT_TOOL_NAME,
        json.dumps(payload, ensure_ascii=False),
    )
    assert out.startswith("OK recorded techno_core event_id=")
    body = store.read_document(TECHNO_CORE_EVENTS_JSONL_RELATIVE_PATH)
    lines = [ln for ln in body.strip().split("\n") if ln.strip()]
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["sphere"] == "living_sphere"
    assert row["source"] == "inner_tick"
    assert row["actor_companion_id"] == cid
    assert row["related_user_id"] == uid
    assert row["summary"] == payload["summary"]
    shutdown_all_memory_stores()


@pytest.mark.asyncio
async def test_techno_core_record_event_rejects_bad_sphere() -> None:
    rid = uuid.uuid4().hex[:12]
    uid, cid, chid = f"u-tce2-{rid}", f"c-tce2-{rid}", f"chat-tce2-{rid}"
    manager = CompanionManager(
        CompanionConfig(
            llm=CompanionLLMConfig(api_key="k"),
            memory_pg_dsn=companion_memory_registry_dsn(),
        )
    )
    session = manager.get_or_create_session(uid, cid, chid)
    store = session.store
    out = await execute_tool_call(
        store,
        TECHNO_CORE_RECORD_EVENT_TOOL_NAME,
        '{"sphere":"not_a_sphere","summary":"x"}',
    )
    assert out.startswith("ERROR:")
    shutdown_all_memory_stores()
