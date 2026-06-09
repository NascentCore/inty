"""Unified tool_background finish envelope resolution (same schema as foreground dual-LLM chat)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.companion_harness.tools.tool_bg_routing import (
    resolve_tool_bg_routing,
)


def _completion_response(
    content: str | None,
    *,
    reasoning: str | None = None,
) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    msg.reasoning = reasoning
    ch = MagicMock()
    ch.message = msg
    resp = MagicMock()
    resp.choices = [ch]
    return resp


def _valid_envelope_dict() -> dict:
    return {
        "user_facing_reply": "hello",
        "importance_round": 5,
        "importance_user_message": 4,
        "importance_assistant_message": 6,
        "output_to_user": True,
    }


@pytest.mark.asyncio
async def test_resolve_tool_bg_routing_uses_final_assistant_json() -> None:
    inner = json.dumps(_valid_envelope_dict(), ensure_ascii=False)
    create_completion = AsyncMock()
    out = await resolve_tool_bg_routing(
        client=None,
        model="m",
        create_completion=create_completion,
        conversation_messages=[],
        final_assistant_content=inner,
    )
    assert out.user_facing_reply == "hello"
    assert out.output_to_user is True
    create_completion.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_tool_bg_routing_strips_json_fence() -> None:
    inner = json.dumps(_valid_envelope_dict(), ensure_ascii=False)
    raw = f"```json\n{inner}\n```"
    create_completion = AsyncMock()
    out = await resolve_tool_bg_routing(
        client=None,
        model="m",
        create_completion=create_completion,
        conversation_messages=[],
        final_assistant_content=raw,
    )
    assert out.user_facing_reply == "hello"
    create_completion.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_tool_bg_routing_fallback_on_invalid_then_conservative() -> None:
    create_completion = AsyncMock(return_value=_completion_response("not json"))
    out = await resolve_tool_bg_routing(
        client=None,
        model="m",
        create_completion=create_completion,
        conversation_messages=[{"role": "user", "content": "hi"}],
        final_assistant_content="not envelope",
    )
    create_completion.assert_called_once()
    assert out.output_to_user is False
    assert out.user_facing_reply == ""
    assert out.importance_round == 5


@pytest.mark.asyncio
async def test_resolve_tool_bg_routing_fallback_returns_parsed_envelope() -> None:
    fb = _valid_envelope_dict()
    fb["output_to_user"] = False
    fb["user_facing_reply"] = "done"
    create_completion = AsyncMock(
        return_value=_completion_response(json.dumps(fb, ensure_ascii=False))
    )
    out = await resolve_tool_bg_routing(
        client=None,
        model="m",
        create_completion=create_completion,
        conversation_messages=[],
        final_assistant_content="{",
    )
    assert out.user_facing_reply == "done"
    assert out.output_to_user is False


@pytest.mark.asyncio
async def test_resolve_tool_bg_routing_fallback_reads_reasoning_envelope() -> None:
    fb = _valid_envelope_dict()
    fb["user_facing_reply"] = "done from reasoning"
    create_completion = AsyncMock(
        return_value=_completion_response(
            None,
            reasoning=json.dumps(fb, ensure_ascii=False),
        )
    )
    out = await resolve_tool_bg_routing(
        client=None,
        model="m",
        create_completion=create_completion,
        conversation_messages=[],
        final_assistant_content="{",
    )
    assert out.user_facing_reply == "done from reasoning"
    assert out.output_to_user is True
