"""Unified tool_background finish envelope resolution (same schema as foreground dual-LLM chat)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from app.core.agentic_kernel.companion.tool_bg_routing import (
    resolve_tool_bg_routing_sync,
)


def _completion_response(content: str | None) -> MagicMock:
    msg = MagicMock()
    msg.content = content
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


def test_resolve_tool_bg_routing_uses_final_assistant_json() -> None:
    inner = json.dumps(_valid_envelope_dict(), ensure_ascii=False)
    create_sync = MagicMock()
    out = resolve_tool_bg_routing_sync(
        client=None,
        model="m",
        create_completion_sync=create_sync,
        conversation_messages=[],
        final_assistant_content=inner,
    )
    assert out.user_facing_reply == "hello"
    assert out.output_to_user is True
    create_sync.assert_not_called()


def test_resolve_tool_bg_routing_strips_json_fence() -> None:
    inner = json.dumps(_valid_envelope_dict(), ensure_ascii=False)
    raw = f"```json\n{inner}\n```"
    create_sync = MagicMock()
    out = resolve_tool_bg_routing_sync(
        client=None,
        model="m",
        create_completion_sync=create_sync,
        conversation_messages=[],
        final_assistant_content=raw,
    )
    assert out.user_facing_reply == "hello"
    create_sync.assert_not_called()


def test_resolve_tool_bg_routing_fallback_on_invalid_then_conservative() -> None:
    create_sync = MagicMock(return_value=_completion_response("not json"))
    out = resolve_tool_bg_routing_sync(
        client=None,
        model="m",
        create_completion_sync=create_sync,
        conversation_messages=[{"role": "user", "content": "hi"}],
        final_assistant_content="not envelope",
    )
    create_sync.assert_called_once()
    assert out.output_to_user is False
    assert out.user_facing_reply == ""
    assert out.importance_round == 5


def test_resolve_tool_bg_routing_fallback_returns_parsed_envelope() -> None:
    fb = _valid_envelope_dict()
    fb["output_to_user"] = False
    fb["user_facing_reply"] = "done"
    create_sync = MagicMock(
        return_value=_completion_response(json.dumps(fb, ensure_ascii=False))
    )
    out = resolve_tool_bg_routing_sync(
        client=None,
        model="m",
        create_completion_sync=create_sync,
        conversation_messages=[],
        final_assistant_content="{",
    )
    assert out.user_facing_reply == "done"
    assert out.output_to_user is False
