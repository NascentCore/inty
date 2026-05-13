from __future__ import annotations

import json

import pytest

from app.core.companion_harness.companion.llm_client import CompanionLLMConfig
from app.core.companion_harness.companion.manager import CompanionConfig, CompanionManager
from app.core.companion_harness.tools.companion_tool_runtime import execute_tool_call
from techno_core.models import TECHNO_CORE_EVENTS_JSONL_RELATIVE_PATH


@pytest.mark.asyncio
async def test_techno_core_record_event_appends_valid_jsonl() -> None:
    manager = CompanionManager(CompanionConfig(llm=CompanionLLMConfig(api_key="k")))
    session = manager.get_or_create_session("u-tce", "c-tce", "chat-tce")
    store = session.store
    payload = {
        "sphere": "living_sphere",
        "summary": "在窗边把杯口的热气吹散了一点。",
        "visibility": "private",
        "related_living_sphere": "玻璃海岸小屋",
    }
    out = await execute_tool_call(
        store,
        "techno_core_record_event",
        json.dumps(payload, ensure_ascii=False),
    )
    assert out.startswith("OK recorded techno_core event_id=")
    body = store.read_document(TECHNO_CORE_EVENTS_JSONL_RELATIVE_PATH)
    lines = [ln for ln in body.strip().split("\n") if ln.strip()]
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["sphere"] == "living_sphere"
    assert row["source"] == "inner_tick"
    assert row["actor_companion_id"] == "c-tce"
    assert row["related_user_id"] == "u-tce"
    assert row["summary"] == payload["summary"]
    manager.shutdown_all()


@pytest.mark.asyncio
async def test_techno_core_record_event_rejects_bad_sphere() -> None:
    manager = CompanionManager(CompanionConfig(llm=CompanionLLMConfig(api_key="k")))
    session = manager.get_or_create_session("u-tce2", "c-tce2", "chat-tce2")
    store = session.store
    out = await execute_tool_call(
        store,
        "techno_core_record_event",
        '{"sphere":"not_a_sphere","summary":"x"}',
    )
    assert out.startswith("ERROR:")
    manager.shutdown_all()
