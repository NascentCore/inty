"""GENERATION tool tag registry."""

from __future__ import annotations

import pytest

from app.core.agentic_kernel.companion.companion_tool_runtime import (
    TOOL_TAG_GENERATION,
    round_includes_generation_tool,
    tool_requires_client_delivery_on_success,
)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("generate_image", True),
        ("modify_image", True),
        ("workspace_read_file", False),
        ("google_web_search", False),
        ("read_web_page", False),
        ("tool_update_agent_status_line", False),
        ("user_profile_record", False),
    ],
)
def test_tool_requires_client_delivery_on_success(name: str, expected: bool) -> None:
    assert tool_requires_client_delivery_on_success(name) is expected


def test_round_includes_generation_tool() -> None:
    assert round_includes_generation_tool(["workspace_read_file", "generate_image"]) is True
    assert round_includes_generation_tool(["user_profile_record"]) is False


def test_generation_tag_constant() -> None:
    assert TOOL_TAG_GENERATION == "GENERATION"
