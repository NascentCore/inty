from __future__ import annotations

from app.techno_core.models import (
    TECHNO_CORE_EVENTS_JSONL_RELATIVE_PATH,
    TECHNO_CORE_RECORD_EVENT_TOOL_NAME,
)

from app.core.companion_harness.companion.prompts.inner_tick_ls_tc import (
    INNER_TICK_LS_TC_AUTONOMY_SECTION,
    INNER_TICK_LS_TC_TOOL_BULLET,
)


def test_inner_tick_ls_tc_substitutes_tool_name_and_events_path() -> None:
    assert TECHNO_CORE_RECORD_EVENT_TOOL_NAME in INNER_TICK_LS_TC_AUTONOMY_SECTION
    assert TECHNO_CORE_EVENTS_JSONL_RELATIVE_PATH in INNER_TICK_LS_TC_AUTONOMY_SECTION
    assert TECHNO_CORE_RECORD_EVENT_TOOL_NAME in INNER_TICK_LS_TC_TOOL_BULLET
