"""Unified tool_background finish envelope resolution (same schema as foreground dual-LLM chat)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
)
from app.core.companion_harness.companion.models import InnerTickActivity
from app.core.companion_harness.companion.dual_llm_chat_branch_envelope import (
    turn_recall_from_envelope,
)
from app.core.companion_harness.tools.tool_bg_routing import (
    resolve_tool_background_finish_envelope,
    resolve_tool_bg_routing_sync,
)

_APP_SLICE = CompanionTurnLangsmithSlice.app_default()


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
        "turn_recall": "",
    }


def test_resolve_tool_background_finish_envelope_skips_routing_for_autonomy() -> (
    None
):
    create_sync = MagicMock()
    out = resolve_tool_background_finish_envelope(
        inner_tick_turn=True,
        inner_tick_activity=InnerTickActivity.AUTONOMY,
        client=None,
        model="m",
        create_completion_sync=create_sync,
        conversation_messages=[],
        final_assistant_content="无",
        langsmith_slice=_APP_SLICE,
    )
    create_sync.assert_not_called()
    assert out.output_to_user is False
    assert out.user_facing_reply == ""
    assert out.importance_round == 5


def test_resolve_tool_background_finish_envelope_routes_for_monolog() -> (
    None
):
    create_sync = MagicMock(return_value=_completion_response("not json"))
    out = resolve_tool_background_finish_envelope(
        inner_tick_turn=True,
        inner_tick_activity=InnerTickActivity.MONOLOG,
        client=None,
        model="m",
        create_completion_sync=create_sync,
        conversation_messages=[],
        final_assistant_content="not envelope",
        langsmith_slice=_APP_SLICE,
    )
    create_sync.assert_called_once()
    assert out.output_to_user is False


def test_resolve_tool_bg_routing_uses_final_assistant_json() -> None:
    inner = json.dumps(_valid_envelope_dict(), ensure_ascii=False)
    create_sync = MagicMock()
    out = resolve_tool_bg_routing_sync(
        client=None,
        model="m",
        create_completion_sync=create_sync,
        conversation_messages=[],
        final_assistant_content=inner,
        langsmith_slice=_APP_SLICE,
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
        langsmith_slice=_APP_SLICE,
    )
    assert out.user_facing_reply == "hello"
    create_sync.assert_not_called()


def test_turn_recall_from_envelope_strips_empty() -> None:
    from app.core.companion_harness.companion.dual_llm_chat_branch_envelope import (
        DualLlmChatBranchEnvelope,
    )

    assert (
        turn_recall_from_envelope(
            DualLlmChatBranchEnvelope(
                importance_round=5,
                importance_user_message=5,
                importance_assistant_message=5,
                turn_recall="",
            )
        )
        is None
    )
    assert (
        turn_recall_from_envelope(
            DualLlmChatBranchEnvelope(
                importance_round=5,
                importance_user_message=5,
                importance_assistant_message=5,
                turn_recall="  用户提到下周见面  ",
            )
        )
        == "用户提到下周见面"
    )


def test_resolve_tool_bg_routing_fallback_on_invalid_then_conservative() -> (
    None
):
    create_sync = MagicMock(return_value=_completion_response("not json"))
    out = resolve_tool_bg_routing_sync(
        client=None,
        model="m",
        create_completion_sync=create_sync,
        conversation_messages=[{"role": "user", "content": "hi"}],
        final_assistant_content="not envelope",
        langsmith_slice=_APP_SLICE,
    )
    create_sync.assert_called_once()
    extra = create_sync.call_args.kwargs["langsmith_extra"]
    assert extra["metadata"]["inty_runtime_channel"] == "app_ws"
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
        langsmith_slice=_APP_SLICE,
    )
    assert out.user_facing_reply == "done"
    assert out.output_to_user is False


def test_resolve_tool_bg_routing_fallback_reads_reasoning_envelope() -> None:
    fb = _valid_envelope_dict()
    fb["user_facing_reply"] = "done from reasoning"
    create_sync = MagicMock(
        return_value=_completion_response(
            None,
            reasoning=json.dumps(fb, ensure_ascii=False),
        )
    )
    out = resolve_tool_bg_routing_sync(
        client=None,
        model="m",
        create_completion_sync=create_sync,
        conversation_messages=[],
        final_assistant_content="{",
        langsmith_slice=_APP_SLICE,
    )
    assert out.user_facing_reply == "done from reasoning"
    assert out.output_to_user is True
