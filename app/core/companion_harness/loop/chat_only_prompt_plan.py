"""Chat-only (no tools) prompt-plan completion for greeting and inner-tick tracks.

Mirrors the legacy single-shot contract per track: greeting uses the dual-LLM
structured envelope; proactive and scheduled use the proactive envelope.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from loguru import logger

from app.core.agentic_companion.types import OutputMessageKind, WireAssistantSource
from app.core.config import global_config_loaded_from_config_yaml
from app.core.companion_harness.companion.dual_llm_chat_branch_envelope import (
    DUAL_LLM_CHAT_RESPONSE_FORMAT,
    split_dual_llm_chat_branch_message,
)
from app.core.companion_harness.companion.in_turn_sync_tool_loop import (
    InTurnSyncToolLoopResult,
)
from app.core.companion_harness.companion.llm_chat_runtime import (
    langsmith_llm_run_id_from_completion,
    langsmith_trace_id_from_completion,
)
from app.core.companion_harness.companion.models import CompanionTurnTrack
from app.core.companion_harness.companion.proactive_chat_envelope import (
    PROACTIVE_CHAT_RESPONSE_FORMAT,
    split_proactive_chat_message,
)
from app.core.companion_harness.loop.context import AgenticLoopContext
from app.core.companion_harness.loop.runtime_system_clauses import (
    apply_agentic_loop_runtime_system_clauses,
)
from app.core.companion_harness.prompt_builder import (
    prompt_messages_to_openai_dicts,
)
from app.core.llms.client import AsyncLlmClient


@dataclass(frozen=True)
class _ChatOnlyTrackEnvelope:
    """Downlink kind and structured-output schema for one chat-only track."""

    downlink_kind: OutputMessageKind
    response_format: dict[str, Any] | None


@dataclass(frozen=True)
class _ChatOnlyParsedAssistant:
    """Assistant body and envelope metadata from one chat-only completion."""

    last_text: str
    skip_final_transcript_assistant_row: bool
    significance_meta: dict[str, Any] | None
    turn_recall: str | None


def _resolve_chat_only_track_envelope(
    track: CompanionTurnTrack,
) -> _ChatOnlyTrackEnvelope:
    match track:
        case CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT:
            return _ChatOnlyTrackEnvelope(
                downlink_kind=OutputMessageKind.PROACTIVE,
                response_format=PROACTIVE_CHAT_RESPONSE_FORMAT,
            )
        case CompanionTurnTrack.INNER_TICK_SCHEDULED:
            return _ChatOnlyTrackEnvelope(
                downlink_kind=OutputMessageKind.SCHEDULED,
                response_format=PROACTIVE_CHAT_RESPONSE_FORMAT,
            )
        case CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING:
            return _ChatOnlyTrackEnvelope(
                downlink_kind=OutputMessageKind.USER_REPLY,
                response_format=DUAL_LLM_CHAT_RESPONSE_FORMAT,
            )
        case _:
            return _ChatOnlyTrackEnvelope(
                downlink_kind=OutputMessageKind.USER_REPLY,
                response_format=None,
            )


async def _invoke_chat_only_llm(
    *,
    track: CompanionTurnTrack,
    llm_client: AsyncLlmClient,
    request_messages: list[dict[str, Any]],
    chat_model: str,
    response_format: dict[str, Any] | None,
    langsmith_extra: dict[str, Any],
    llm_scene: str,
    high_reasoning: bool,
    trace_id: str,
) -> Any:
    match track:
        case CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING:
            greet_cfg = (
                global_config_loaded_from_config_yaml.agent.companion_harness.implicit_sign_on_greeting
            )
            return await llm_client.chat_completion_with_retrial(
                messages=request_messages,
                model=chat_model,
                tools=None,
                tool_choice=None,
                response_format=response_format,
                scene=llm_scene,
                langsmith_extra=langsmith_extra,
                high_reasoning=high_reasoning,
                max_attempts=int(greet_cfg.llm_max_attempts),
                per_attempt_timeout_sec=float(greet_cfg.llm_timeout_sec),
                trace_id=trace_id,
                attempt_log_label="implicit_sign_on_greeting",
            )
        case _:
            return await llm_client.chat_completion(
                messages=request_messages,
                model=chat_model,
                tools=None,
                response_format=response_format,
                langsmith_extra=langsmith_extra,
                high_reasoning=high_reasoning,
                scene=llm_scene,
            )


def _parse_chat_only_assistant_message(
    *,
    track: CompanionTurnTrack,
    msg: Any,
    trace_id: str,
) -> _ChatOnlyParsedAssistant:
    match track:
        case (
            CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT
            | CompanionTurnTrack.INNER_TICK_SCHEDULED
        ):
            proactive_split = split_proactive_chat_message(msg)
            if proactive_split.output_to_user:
                return _ChatOnlyParsedAssistant(
                    last_text=proactive_split.visible_text,
                    skip_final_transcript_assistant_row=False,
                    significance_meta=None,
                    turn_recall=None,
                )
            return _ChatOnlyParsedAssistant(
                last_text="",
                skip_final_transcript_assistant_row=True,
                significance_meta=None,
                turn_recall=None,
            )
        case CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING:
            dual_split = split_dual_llm_chat_branch_message(msg)
            if dual_split.output_to_user is False:
                logger.warning(
                    "chat_only_prompt_plan dual_llm envelope output_to_user=false "
                    "trace_id={} (expected true for greeting)",
                    trace_id,
                )
            return _ChatOnlyParsedAssistant(
                last_text=dual_split.visible_text,
                skip_final_transcript_assistant_row=False,
                significance_meta=dual_split.significance_meta,
                turn_recall=dual_split.turn_recall,
            )
        case _:
            return _ChatOnlyParsedAssistant(
                last_text=(msg.content or "").strip(),
                skip_final_transcript_assistant_row=False,
                significance_meta=None,
                turn_recall=None,
            )


async def run_chat_only_prompt_plan(
    context: AgenticLoopContext,
    *,
    llm_client: AsyncLlmClient,
    appender,
) -> InTurnSyncToolLoopResult:
    """Single chat completion (no tools) for greeting and inner-tick chat-only tracks."""
    assert context.prompt_plan is not None
    track = context.companion_turn_track
    execution = context.execution
    request_messages = prompt_messages_to_openai_dicts(
        context.prompt_plan.messages
    )
    apply_agentic_loop_runtime_system_clauses(
        openai_messages=request_messages,
        user_text=context.user_text,
    )
    chat_model = llm_client.resolve_model("chat")
    langsmith_extra = context.langsmith.turn_slice.foreground_invocation_extra(
        source=execution.foreground_source.value,
        extra_metadata=None,
    )
    envelope = _resolve_chat_only_track_envelope(track)
    t_api = time.perf_counter()
    resp = await _invoke_chat_only_llm(
        track=track,
        llm_client=llm_client,
        request_messages=request_messages,
        chat_model=chat_model,
        response_format=envelope.response_format,
        langsmith_extra=langsmith_extra,
        llm_scene=execution.llm_scene.value,
        high_reasoning=execution.high_reasoning,
        trace_id=context.trace_id,
    )
    langsmith_trace_acc = langsmith_trace_id_from_completion(resp) or ""
    langsmith_llm_run_acc = langsmith_llm_run_id_from_completion(resp) or ""
    msg = resp.choices[0].message
    parsed = _parse_chat_only_assistant_message(
        track=track,
        msg=msg,
        trace_id=context.trace_id,
    )
    approx_ctx_chars = sum(
        len(str(m.get("content") or "")) for m in request_messages
    )
    logger.info(
        "chat_only_prompt_plan llm_done model={} chat_completions_ms={:.0f} "
        "approx_ctx_chars={} trace_id={} track={}",
        chat_model,
        (time.perf_counter() - t_api) * 1000.0,
        approx_ctx_chars,
        context.trace_id,
        track.value,
    )
    if parsed.last_text:
        wire_source = (
            WireAssistantSource.GREETING
            if track == CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING
            else WireAssistantSource.CHAT
        )
        await appender.append_visible_message(
            kind=envelope.downlink_kind,
            text=parsed.last_text,
            trace_id=context.trace_id,
            langsmith_trace_id=langsmith_trace_acc,
            langsmith_run_id=langsmith_llm_run_acc,
            turn_recall=parsed.turn_recall,
            wire_assistant_source=wire_source,
        )
    return InTurnSyncToolLoopResult(
        assistant_text=parsed.last_text,
        langsmith_trace_id=langsmith_trace_acc,
        langsmith_run_id=langsmith_llm_run_acc,
        skip_final_transcript_assistant_row=parsed.skip_final_transcript_assistant_row,
        last_interim_assistant_msg_uuid=None,
        loop_persisted_user_transcript=False,
        significance_meta=parsed.significance_meta,
        turn_recall=parsed.turn_recall,
    )
