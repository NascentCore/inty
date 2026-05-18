"""BGM catalog system slice for tool-background LLM stack."""

from __future__ import annotations

from typing import Any

from app.core.companion_harness.companion.bgm_library import (
    SET_BGM_TOOL_NAME,
    format_bgm_catalog_for_system_message,
)


def build_bgm_system_message() -> dict[str, Any]:
    catalog = format_bgm_catalog_for_system_message()
    body = (
        "## Conversation background music (BGM)\n\n"
        "The catalog below lists preset tracks. Choose at most one track per tool-background "
        f"round when the recent conversation mood clearly calls for new BGM, or when silence "
        f"would feel wrong and no current BGM fits.\n\n"
        f"Do **not** call `{SET_BGM_TOOL_NAME}` every round just because tools are required. "
        "When you call it, pass a valid `track_id` from the list and a short internal `reason`. "
        "Set `output_to_user` to false in the finish envelope unless you also owe the user words. "
        "Do not tell the user about system BGM mechanics.\n\n"
        "### Catalog\n"
        f"{catalog}\n"
    )
    return {"role": "system", "content": body}
