"""Resolve async tool_background finish using the unified dual-LLM JSON envelope.

The model's final assistant message must validate as ``DualLlmChatBranchEnvelope``
(same schema as foreground ``DUAL_LLM_CHAT_RESPONSE_FORMAT``). If invalid, one
extra no-tools completion runs with the same ``response_format`` and a short
system instruction. The fallback completion accepts validated envelopes from
``message.content`` or provider reasoning side channels.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.core.companion_harness.companion.dual_llm_chat_branch_envelope import (
    DUAL_LLM_CHAT_RESPONSE_FORMAT,
    DualLlmChatBranchEnvelope,
    parse_dual_llm_chat_envelope_from_message,
    parse_dual_llm_chat_envelope_json,
)
from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
)
from app.core.companion_harness.companion.models import (
    InnerTickActivity,
    inner_tick_activity_suppresses_user_delivery,
)
from app.core.companion_harness.llm.langsmith_invocation_extra import (
    SOURCE_TOOL_BACKGROUND_ROUTING_FALLBACK,
)

_UNIFIED_FALLBACK_SYSTEM_PROMPT = (
    "## Tool loop finished (machine-readable envelope)\n\n"
    "The tool execution loop has finished. Respond with **JSON only** (no markdown fences, "
    "no extra prose). Use the **same** shape as the dual-LLM chat envelope:\n"
    "- `user_facing_reply` (string): concise visible summary for a follow-up bubble when needed; "
    "may be empty when images or artifacts alone suffice.\n"
    "- `importance_round`, `importance_user_message`, `importance_assistant_message` "
    "(integers 1-10): score this tool-finish moment per significance perception rules.\n"
    "- `output_to_user` (boolean): **true** if the user should see a follow-up bubble with tool "
    "outcomes (read_file, list_dir, search, generated assets, etc.). **false** when "
    "only silent persistence ran and no recap is needed.\n"
    "Successful image generation still delivers the asset; `output_to_user` only gates extra text.\n"
)


def _conservative_tool_finish_envelope() -> DualLlmChatBranchEnvelope:
    return DualLlmChatBranchEnvelope(
        user_facing_reply="",
        importance_round=5,
        importance_user_message=5,
        importance_assistant_message=5,
        output_to_user=False,
    )


def resolve_tool_background_finish_envelope(
    *,
    inner_tick_turn: bool,
    inner_tick_activity: InnerTickActivity,
    client: Any,
    model: str,
    create_completion_sync: Any,
    conversation_messages: list[dict[str, Any]],
    final_assistant_content: str,
    trace_id: str | None = None,
    langsmith_slice: CompanionTurnLangsmithSlice,
) -> DualLlmChatBranchEnvelope:
    """Resolve tool_background finish envelope.

    Inner-tick activities that suppress client delivery (``AUTONOMY``) never need
    routing LLM: ``output_to_user`` and recap text do not affect WS or transcript policy.
    """
    tid = trace_id or "-"
    if inner_tick_turn and inner_tick_activity_suppresses_user_delivery(
        inner_tick_activity
    ):
        logger.debug(
            "tool_bg_routing trace_id={} source=delivery_suppressed_skip_routing "
            "inner_tick_activity={}",
            tid,
            inner_tick_activity.value,
        )
        return _conservative_tool_finish_envelope()
    return resolve_tool_bg_routing_sync(
        client=client,
        model=model,
        create_completion_sync=create_completion_sync,
        conversation_messages=conversation_messages,
        final_assistant_content=final_assistant_content,
        trace_id=trace_id,
        langsmith_slice=langsmith_slice,
    )


def resolve_tool_bg_routing_sync(
    *,
    client: Any,
    model: str,
    create_completion_sync: Any,
    conversation_messages: list[dict[str, Any]],
    final_assistant_content: str,
    trace_id: str | None = None,
    langsmith_slice: CompanionTurnLangsmithSlice,
) -> DualLlmChatBranchEnvelope:
    """
    Prefer unified envelope JSON from the model's final assistant message; if missing/invalid,
    run one extra completion (no tools, same ``response_format`` as foreground chat).

    trace_id: optional correlation id for DEBUG logs (tool_bg_routing / repl.turn.bg policy).
    """
    tid = trace_id or "-"
    parsed = parse_dual_llm_chat_envelope_json(final_assistant_content)
    if parsed is not None:
        logger.debug(
            "tool_bg_routing trace_id={} source=final_assistant_message "
            "output_to_user={} user_facing_reply_chars={}",
            tid,
            parsed.output_to_user,
            len(parsed.user_facing_reply or ""),
        )
        return parsed
    logger.debug(
        "tool_bg_routing trace_id={} source=extra_completion_request "
        "(final_assistant_not_valid_unified_envelope_json)",
        tid,
    )
    routing_tail = [
        {"role": "system", "content": _UNIFIED_FALLBACK_SYSTEM_PROMPT}
    ]
    payload = [
        {k: v for k, v in m.items() if not str(k).startswith("_")}
        for m in conversation_messages
    ]
    payload.extend(routing_tail)
    resp = create_completion_sync(
        client,
        model=model,
        messages_payload=payload,
        tools=[],
        response_format=DUAL_LLM_CHAT_RESPONSE_FORMAT,
        langsmith_extra=langsmith_slice.tool_call_extra(
            phase_suffix=SOURCE_TOOL_BACKGROUND_ROUTING_FALLBACK,
            extra_metadata=None,
        ),
    )
    fallback = parse_dual_llm_chat_envelope_from_message(
        resp.choices[0].message
    )
    if fallback is not None:
        logger.debug(
            "tool_bg_routing trace_id={} source=extra_completion_response "
            "output_to_user={} user_facing_reply_chars={}",
            tid,
            fallback.output_to_user,
            len(fallback.user_facing_reply or ""),
        )
        return fallback
    logger.debug(
        "tool_bg_routing trace_id={} source=fallback_conservative_invalid_json",
        tid,
    )
    return _conservative_tool_finish_envelope()
