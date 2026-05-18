from __future__ import annotations

import json

from living_sphere.models import (
    LIVING_SPHERE_UPDATES_JSONL_RELATIVE_PATH,
    LivingSphereUpdate,
)


def test_living_sphere_update_round_trip_json() -> None:
    row = LivingSphereUpdate(
        change_request="在窗边加一盏暖色台灯",
        user_msg_uuid="um-1",
        trace_id="tr-1",
    )
    payload = row.model_dump(mode="json")
    assert payload["source"] == "chat_tool"
    assert payload["change_request"] == "在窗边加一盏暖色台灯"
    line = json.dumps(payload, ensure_ascii=False)
    restored = LivingSphereUpdate.model_validate(json.loads(line))
    assert restored.update_id == row.update_id
    assert restored.user_msg_uuid == "um-1"
    assert LIVING_SPHERE_UPDATES_JSONL_RELATIVE_PATH == "living_sphere_updates.jsonl"
