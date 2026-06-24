"""Dual-LLM async foreground chat leg (envelope completion + tool-path handoff).

Extracted from turn.run_turn ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL for reuse by
the production AgenticLoop. Does not start tool_background; caller passes
tool_msgs_for_bg into run_tool_background_loop or start_tool_background_job.

TODO(!3630): Build langsmith_extra via LlmInvocationContext instead of langsmith_slice helpers here.
TODO(!3632): Callers should prefer inline run_tool_background_loop via AgenticLoop only.
"""

from __future__ import annotations

import asyncio
import time
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from loguru import logger

from app.core.companion_harness.llm.langsmith_invocation_extra import (
    SOURCE_FOREGROUND_DUAL_LLM_ENVELOPE,
)
from app.utils.models_catalog import GenAIModel
from .dual_llm_chat_branch_envelope import (
    DUAL_LLM_CHAT_RESPONSE_FORMAT,
    split_dual_llm_chat_branch_message,
)
from .langsmith_turn_slice import CompanionTurnLangsmithSlice
from .llm_chat_runtime import (
    langsmith_llm_run_id_from_completion,
    langsmith_trace_id_from_completion,
)
from app.core.llms.client import LlmClient
from .llm_runtime_events import record_llm_inference_failure
from .models import InnerTickActivity

CHAT_TRACK_RESPONSE_MESSAGE_TITLE = "## Response from the chat track"


def build_chat_track_handoff_assistant_message(
    *, fg_text: str
) -> dict[str, Any]:
    """OpenAI assistant row injected into tool-path messages after foreground chat."""
    assert fg_text
    return {
        "role": "assistant",
        "content": f"{CHAT_TRACK_RESPONSE_MESSAGE_TITLE}\n\n{fg_text}",
    }


@dataclass(frozen=True)
class DualLlmForegroundChatInput:
    """Inputs for one dual-LLM foreground chat envelope call."""

    llm_client: LlmClient
    chat_msgs: tuple[dict[str, Any], ...]
    tool_msgs: tuple[dict[str, Any], ...]
    chat_model: GenAIModel
    langsmith_slice: CompanionTurnLangsmithSlice
    foreground_scene: str  # ``LLM_SCENE_CHAT`` or ``LLM_SCENE_INNER_TICK``
    high_reasoning: bool
    trace_id: str
    skip_foreground_envelope: bool
    route_inner_activity: InnerTickActivity
    langsmith_trace_id: str
    langsmith_run_id: str


@dataclass(frozen=True)
class DualLlmForegroundChatResult:
    """Foreground leg outputs and tool-path messages for handoff."""

    assistant_text: str
    significance_meta: dict[str, Any] | None
    turn_recall: str | None
    tool_msgs_for_bg: tuple[dict[str, Any], ...]
    force_tools_first_round: bool
    langsmith_trace_id: str
    langsmith_run_id: str


async def run_dual_llm_foreground_chat(
    fg_input: DualLlmForegroundChatInput,
) -> DualLlmForegroundChatResult:
    """Run foreground dual-LLM envelope chat or skip (maintenance inner tick).

    When ``skip_foreground_envelope`` is true, returns empty foreground text and deep-copied
    ``tool_msgs`` with ``force_tools_first_round=True``. Otherwise performs one chat completion,
    parses the envelope, and appends the chat-track handoff assistant row to tool messages when
    foreground text is non-empty.
    """
    langsmith_trace_acc = fg_input.langsmith_trace_id
    langsmith_run_acc = fg_input.langsmith_run_id

    if fg_input.skip_foreground_envelope:
        logger.info(
            "run_dual_llm_foreground_chat skip foreground envelope "
            "inner_tick_activity={} model_chat={}",
            fg_input.route_inner_activity.value,
            fg_input.chat_model,
        )
        return DualLlmForegroundChatResult(
            assistant_text="",
            significance_meta=None,
            turn_recall=None,
            tool_msgs_for_bg=tuple(deepcopy(list(fg_input.tool_msgs))),
            force_tools_first_round=True,
            langsmith_trace_id=langsmith_trace_acc,
            langsmith_run_id=langsmith_run_acc,
        )

    chat_msgs = list(fg_input.chat_msgs)
    t_api = time.perf_counter()
    chat_model = fg_input.chat_model
    llm_client = fg_input.llm_client

    def _chat_sync() -> Any:
        return llm_client.chat_completion(
            messages=chat_msgs,
            model=chat_model,
            tools=None,
            response_format=DUAL_LLM_CHAT_RESPONSE_FORMAT,
            scene=fg_input.foreground_scene,
            langsmith_extra=fg_input.langsmith_slice.foreground_invocation_extra(
                source=SOURCE_FOREGROUND_DUAL_LLM_ENVELOPE,
                extra_metadata=None,
            ),
            high_reasoning=fg_input.high_reasoning,
        )

    try:
        resp = await asyncio.wait_for(
            asyncio.to_thread(_chat_sync),
            timeout=llm_client.config.async_chat_front_timeout_sec,
        )
        tid = langsmith_trace_id_from_completion(resp)
        if tid:
            langsmith_trace_acc = tid
        ls_lr = langsmith_llm_run_id_from_completion(resp)
        if ls_lr:
            langsmith_run_acc = ls_lr
    except TimeoutError as exc:
        record_llm_inference_failure(
            model=chat_model.id_on_provider,
            exc=exc,
            foreground_timeout_sec=llm_client.config.async_chat_front_timeout_sec,
        )
        raise RuntimeError(
            f"async chat front timed out after "
            f"{llm_client.config.async_chat_front_timeout_sec:.0f}s "
            f"(trace_id={fg_input.trace_id})"
        ) from exc

    approx_ctx_chars = sum(len(str(m.get("content") or "")) for m in chat_msgs)
    logger.info(
        "run_dual_llm_foreground_chat llm_round={} model={} chat_completions_ms={:.0f} "
        "approx_ctx_chars={} async_chat_tool_background foreground_chat scene={}",
        1,
        chat_model,
        (time.perf_counter() - t_api) * 1000.0,
        approx_ctx_chars,
        fg_input.foreground_scene,
    )
    msg = resp.choices[0].message
    dual_split = split_dual_llm_chat_branch_message(msg)
    assistant_text = dual_split.visible_text
    significance_meta = dual_split.significance_meta
    turn_recall = dual_split.turn_recall
    fg_output_to_user = dual_split.output_to_user
    if fg_output_to_user is False:
        logger.warning(
            "run_dual_llm_foreground_chat envelope output_to_user=false "
            "trace_id={} (expected true for chat branch)",
            fg_input.trace_id,
        )
    fg_text = assistant_text.strip()
    tool_msgs_for_bg = deepcopy(list(fg_input.tool_msgs))
    if fg_text:
        tool_msgs_for_bg.append(
            build_chat_track_handoff_assistant_message(fg_text=fg_text)
        )
    force_tools_first_round = not bool(fg_text)
    return DualLlmForegroundChatResult(
        assistant_text=assistant_text,
        significance_meta=significance_meta,
        turn_recall=turn_recall,
        tool_msgs_for_bg=tuple(tool_msgs_for_bg),
        force_tools_first_round=force_tools_first_round,
        langsmith_trace_id=langsmith_trace_acc,
        langsmith_run_id=langsmith_run_acc,
    )
